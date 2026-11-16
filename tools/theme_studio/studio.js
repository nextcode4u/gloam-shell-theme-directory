/* SPDX-License-Identifier: GPL-3.0-or-later */
"use strict";
document.getElementById("help").onclick = () =>
  window.open("/guide", "_blank", "noopener");
const $ = (id) => document.getElementById(id),
  token = document.body.dataset.token;
let state,
  section = "project",
  activeStage = "preview",
  activeAsset = "icons/folder.png",
  selectedSlot = "icons/folder.png",
  assetBinding = null,
  rawDraft = null,
  fontRole = "ui",
  audioRole = "music",
  loadedAsset = "icons/folder.png",
  installRoot = "",
  nativeExecutable = "",
  serial = 0,
  previewTimer,
  savedTimer;
let controlId = 0;
let pending = Promise.resolve(),
  dirtyArt = false,
  paintHistory = [],
  paintFuture = [],
  layers = [],
  layerIndex = 0,
  artWidth = 32,
  artHeight = 32;
const sections = [
  [
    "project",
    "◕",
    "Project",
    "Start, import or resume",
    "Keep source artwork and editable settings in one working folder.",
  ],
  [
    "colors",
    "◐",
    "Palette",
    "Color roles",
    "Independent colors, inheritance and native contrast checks.",
  ],
  [
    "layout",
    "▤",
    "Layout",
    "Screen composition",
    "Choose Gloam’s bounded compositions, navigation and browser defaults.",
  ],
  [
    "backgrounds",
    "▧",
    "Backgrounds",
    "Artwork & surfaces",
    "Import, crop, paint or generate full-screen reading surfaces.",
  ],
  [
    "icons",
    "▦",
    "Icons",
    "File & tab icons",
    "29 independent slots. Import illustrations, split an atlas or paint your own.",
  ],
  [
    "components",
    "▱",
    "Components",
    "Materials & controls",
    "Skins, borders, cards, status glyphs and controls with four-level coverage.",
  ],
  [
    "fonts",
    "Aa",
    "Typography",
    "Body & headings",
    "Convert a font or import a prepared face. Keep the font’s full license.",
  ],
  [
    "audio",
    "♫",
    "Audio",
    "Music & UI sounds",
    "Trim, mix down, resample and loop with runtime limits checked.",
  ],
  [
    "motion",
    "◌",
    "Motion",
    "Ambient & focus",
    "Small bounded accents and focus feedback; Reduced motion stays available.",
  ],
  [
    "splash",
    "▶",
    "Startup splash",
    "Splash designer",
    "Create animation in the shared designer, then build it into this theme.",
  ],
  [
    "manifest",
    "≡",
    "Manifest",
    "Direct INI editing",
    "Use the same fields as the visual controls. No theme scripts are executed.",
  ],
  [
    "publish",
    "↗",
    "Publish",
    "Check & export",
    "Prepare fast-loading assets, retain notices and install only this theme.",
  ],
];
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else if (key === "text") node.textContent = value;
    else if (key in node) node[key] = value;
    else node.setAttribute(key, value);
  }
  for (const c of children.flat()) {
    if (c != null)
      node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return node;
}
function button(label, fn, primary = false) {
  return el("button", {
    text: label,
    class: primary ? "primary" : "",
    onclick: () => guard(fn),
  });
}
function toast(text) {
  $("toast").textContent = text;
  $("toast").classList.add("show");
  clearTimeout(savedTimer);
  savedTimer = setTimeout(() => $("toast").classList.remove("show"), 3500);
}
function log(text, kind = "ok") {
  const row = el("div", { class: "log-" + kind, text });
  $("activity").append(row);
  while ($("activity").children.length > 120) $("activity").firstChild.remove();
  $("activity").scrollTop = $("activity").scrollHeight;
  if (kind === "error")
    document.querySelector(".activity").classList.add("open");
}
async function guard(fn) {
  try {
    return await fn();
  } catch (error) {
    if (error instanceof CanceledEdit) {
      saveStatus();
      return null;
    }
    log(error.message, "error");
    toast(error.message);
    $("save-state").textContent = "Action needs attention";
    return null;
  }
}
class CanceledEdit extends Error {}
function saveStatus() {
  $("save-state").textContent = dirtyArt
    ? "Unsaved artwork"
    : rawDraft !== null
      ? "Unsaved manifest"
      : "Saved locally";
}
function editDecision(message) {
  return new Promise((resolve) => {
    const modal = el(
      "dialog",
      { class: "edit-decision" },
      el("h2", { text: "Unsaved changes" }),
      el("p", { text: message }),
    );
    const finish = (value) => {
      modal.close();
      modal.remove();
      resolve(value);
    };
    modal.append(
      row(
        button("Save and continue", () => finish("save"), true),
        button("Discard changes", () => finish("discard")),
        button("Cancel", () => finish("cancel")),
      ),
    );
    modal.addEventListener("cancel", (event) => {
      event.preventDefault();
      finish("cancel");
    });
    document.body.append(modal);
    modal.showModal();
  });
}
async function settleEdits(art = true, manifest = false) {
  if (!(art && dirtyArt) && !(manifest && rawDraft !== null)) return;
  const choice = await editDecision(
    "Save your current edits before continuing, discard them, or keep editing.",
  );
  if (choice === "cancel") throw new CanceledEdit();
  if (choice === "save") {
    if (art && dirtyArt) await saveArtwork();
    if (manifest && rawDraft !== null) await saveManifest();
  } else {
    if (art && dirtyArt) {
      dirtyArt = false;
      layers = [];
      setStage("preview");
    }
    if (manifest) rawDraft = null;
  }
  saveStatus();
}
async function saveManifest() {
  if (rawDraft === null) return;
  const text = rawDraft;
  await api("save", { raw: text }, false);
  rawDraft = null;
  saveStatus();
}
function url(endpoint, params = {}) {
  return endpoint + "?" + new URLSearchParams({ ...params, token, v: serial });
}
function assetUrl(path) {
  return url("/api/asset", { path });
}
async function api(action, data = {}, refresh = true) {
  const mutations = [
    "image",
    "material",
    "generate",
    "atlas",
    "remove",
    "copy",
    "upload",
    "undo",
    "redo",
    "workspace",
    "import",
  ];
  if (mutations.includes(action))
    await settleEdits(
      true,
      ["undo", "redo", "workspace", "import"].includes(action),
    );
  if (["export", "install", "native", "prepare"].includes(action)) {
    if (dirtyArt) await saveArtwork();
    await saveManifest();
  }
  const shouldReload =
    layers.length &&
    mutations.includes(action) &&
    (["undo", "redo"].includes(action) ||
      data.path === activeAsset ||
      data.targets?.includes(activeAsset) ||
      (data.kind &&
        activeAsset.startsWith(
          (state.config[data.kind]?.directory || data.kind) + "/",
        )));
  const reload = {
    path: activeAsset,
    width: artWidth,
    height: artHeight,
    binding: assetBinding,
  };
  const task = async () => {
    $("save-state").textContent = "Working…";
    const response = await fetch("/api/action", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Studio-Token": token },
      body: JSON.stringify({ action, ...data }),
    });
    const result = await response.json();
    if (!response.ok) throw Error(result.error || "Action failed");
    if (result.state) {
      if (action === "workspace") installRoot = "";
      state = result.state;
      serial++;
      updateShell();
      if (refresh) inspect();
      renderAssets();
      refreshPreview();
    }
    saveStatus();
    return result.result;
  };
  const current = pending.then(task);
  pending = current.catch(() => {});
  const result = await current;
  if (shouldReload) {
    dirtyArt = false;
    await editAsset(reload.path, reload.width, reload.height, reload.binding);
  }
  return result;
}
function updateShell() {
  $("project-name").textContent = state.config.theme?.name || state.id;
  $("workspace-path").textContent = state.workspace;
  $("undo").disabled = !state.undo;
  $("redo").disabled = !state.redo;
  $("error-count").textContent = state.report.errors.length
    ? state.report.errors.length + " errors"
    : "No blocking errors";
}
function refreshPreview() {
  clearTimeout(previewTimer);
  previewTimer = setTimeout(() => {
    if (!state) return;
    document.querySelector(".caption").textContent =
      "256 × 192 · authoring preview · validate on the console";
    $("preview-loading").textContent = "Preparing preview…";
    const image = $("preview");
    image.onload = () => ($("preview-loading").textContent = "");
    image.onerror = () =>
      ($("preview-loading").textContent =
        "Preview unavailable — check theme values.");
    image.src = url("/api/preview", {
      sample: $("sample").value,
      view: $("preview-view").value,
      selected: $("selected").value,
      guides: $("guides").checked ? "1" : "0",
    });
  }, 180);
}
function setStage(name) {
  activeStage = name;
  for (const item of ["preview", "canvas", "assets"])
    $(item + "-stage").classList.toggle("hidden", item !== name);
  document
    .querySelectorAll("[data-stage]")
    .forEach((b) => b.classList.toggle("selected", b.dataset.stage === name));
  if (name === "assets") renderAssets();
}
function selectSection(name) {
  return guard(async () => {
    if (name !== section && rawDraft !== null) await settleEdits(false, true);
    section = name;
    if (
      ["icons", "components"].includes(name) &&
      !selectedSlot.startsWith((state.config[name]?.directory || name) + "/")
    )
      selectedSlot =
        (state.config[name]?.directory || name) + "/" + state[name][0] + ".png";
    document
      .querySelectorAll("[data-section]")
      .forEach((b) => b.classList.toggle("active", b.dataset.section === name));
    inspect();
  });
}
function field(label, input, help = "") {
  const target = ["INPUT", "SELECT", "TEXTAREA"].includes(input.tagName)
    ? input
    : input.querySelector("input,select,textarea");
  if (target && !target.id) target.id = "control-" + ++controlId;
  return el(
    "div",
    { class: "field" },
    el("label", { text: label, htmlFor: target?.id || "" }),
    input,
    help ? el("small", { text: help }) : null,
  );
}
function number(label, value, min, max, step = 1) {
  const input = el("input", { type: "number", value, min, max, step });
  return [field(label, input), input];
}
function row(...items) {
  return el("div", { class: "button-row" }, items);
}
function group(title, ...children) {
  return el("section", { class: "group" }, el("h3", { text: title }), children);
}
function note(text) {
  return el("div", { class: "notice", text });
}
function select(values, value) {
  return el(
    "select",
    {},
    values.map((v) =>
      el("option", { value: v, text: v, selected: v === value }),
    ),
  );
}
async function pick(kind, title) {
  return await api("choose", { kind, title }, false);
}
async function upload(accept) {
  return new Promise((resolve) => {
    const input = $("file-picker");
    input.value = "";
    input.accept = accept;
    input.oncancel = () => resolve(null);
    input.onchange = () => resolve(input.files[0] || null);
    input.click();
  });
}
async function fileData(file) {
  if (file.size > 32 * 1024 * 1024) throw Error("File exceeds 32 MiB.");
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(Error("Could not read file"));
    reader.readAsDataURL(file);
  });
}
async function loadImage(source) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(Error("Image could not be decoded."));
    image.src = source;
  });
}
function pathPicker(value = "", kind = "directory") {
  const input = el("input", {
    value,
    placeholder: kind === "file" ? "File path…" : "Folder path…",
  });
  return {
    input,
    node: el(
      "div",
      { class: "input-row" },
      input,
      button("Browse…", async () => {
        const path = await pick(
          kind,
          "Choose " + (kind === "file" ? "a file" : "a folder"),
        );
        if (path) {
          input.value = path;
          input.dispatchEvent(new Event("input"));
        }
      }),
    ),
  };
}
function renderFields(container, name, keys = null) {
  const specs = state.schema[name];
  for (const [key, spec] of Object.entries(specs)) {
    if (keys && !keys.includes(key)) continue;
    const current = state.config[name] || {},
      present = Object.hasOwn(current, key),
      value = current[key] ?? spec.default ?? "";
    let control, input;
    if (spec.type === "choice") {
      input = select(spec.choices, value);
      control = input;
    } else if (spec.type === "color") {
      input = el("input", { value, placeholder: "#RRGGBB" });
      const color = el("input", {
        type: "color",
        value: /^#[a-f\d]{6}$/i.test(value) ? value : "#000000",
      });
      color.oninput = () => (input.value = color.value);
      color.onchange = () => save(color.value);
      input.oninput = () => {
        if (/^#[a-f\d]{6}$/i.test(input.value)) color.value = input.value;
      };
      control = el("div", { class: "input-row" }, color, input);
    } else {
      input = el("input", {
        type: spec.type === "number" ? "number" : "text",
        value,
        placeholder: spec.type === "path" ? "Theme-relative path" : "Inherit",
        min: spec.min,
        max: spec.max,
      });
      control = input;
    }
    const save = (value) =>
      guard(async () => {
        await api("field", { section: name, key, value }, false);
        const inherit = input.closest(".field").querySelector(".inherit input");
        if (inherit) inherit.checked = false;
      });
    input.onchange = () => save(input.value);
    input.id = "control-" + ++controlId;
    const children = [
      el("label", { text: key.replaceAll("_", " "), htmlFor: input.id }),
      control,
    ];
    if (!(name === "theme" && key === "version")) {
      const inherit = el("input", {
        type: "checkbox",
        checked: !present,
        onchange: (event) =>
          guard(() =>
            api("field", {
              section: name,
              key,
              inherit: event.target.checked,
              value: input.value,
            }),
          ),
      });
      children.push(
        el("label", { class: "inherit" }, inherit, "Inherit / omit"),
      );
    }
    if (spec.help) children.push(el("small", { text: spec.help }));
    container.append(el("div", { class: "field" }, children));
  }
}
function inspect() {
  if (!state) return;
  const desc = sections.find((s) => s[0] === section);
  $("section-kicker").textContent = desc[2].toUpperCase();
  $("section-title").textContent = desc[3];
  $("section-description").textContent = desc[4];
  const host = $("inspector-content");
  host.replaceChildren();
  if (section === "project") projectInspector(host);
  else if (section === "colors") {
    host.append(
      row(
        ...Object.keys(state.palettes).map((name) =>
          button(name, () => api("palette", { name })),
        ),
      ),
    );
    host.append(button("Extract colors from an image…", extractPalette));
    renderFields(host, "colors");
  } else if (section === "layout") {
    host.append(
      note(
        "Scene artwork boxes can be moved in the preview with Safe areas enabled. Required controls keep their native bounds.",
      ),
    );
    renderFields(host, "layout");
  } else if (section === "backgrounds") backgroundInspector(host);
  else if (section === "icons" || section === "components")
    spriteInspector(host, section);
  else if (section === "fonts") fontInspector(host);
  else if (section === "audio") audioInspector(host);
  else if (section === "motion") motionInspector(host);
  else if (section === "splash") splashInspector(host);
  else if (section === "manifest") {
    const raw = el("textarea", {
      class: "raw mono",
      value: rawDraft ?? state.raw,
      spellcheck: false,
    });
    raw.oninput = () => {
      rawDraft = raw.value;
      saveStatus();
    };
    host.append(
      field("theme.ini", raw),
      button(
        "Apply INI",
        async () => {
          rawDraft = raw.value;
          await saveManifest();
          inspect();
        },
        true,
      ),
      note(
        "Applying visual edits rewrites the INI in canonical form. Keep prose and licensing notes in credits files.",
      ),
    );
  } else if (section === "publish") publishInspector(host);
}
async function importTheme(path) {
  await api("import", { path });
  layers = [];
  dirtyArt = false;
  setStage("preview");
}
function projectInspector(host) {
  const id = el("input", { value: state.id });
  const author = el("input", { value: state.metadata.author || "" });
  const license = el("input", {
    value: state.metadata.license || "",
    placeholder: "Your asset license / mixed terms",
  });
  const desc = el("textarea", { value: state.metadata.description || "" });
  const credits = el("textarea", {
    value: state.metadata.credits || "",
    placeholder:
      "Credit each font, image, recording and contributor. Include source links and full license files.",
  });
  for (const input of [id, author, license, desc, credits]) {
    input.onchange = () =>
      guard(() =>
        api(
          "save",
          {
            id: id.value,
            metadata: {
              author: author.value,
              license: license.value,
              description: desc.value,
              credits: credits.value,
            },
          },
          false,
        ),
      );
  }
  host.append(
    field(
      "Folder ID",
      id,
      "ASCII letters, numbers, hyphens and underscores; 1–63 bytes.",
    ),
    field("Author", author),
    field("Asset terms", license),
    field("Description", desc),
    field("Credits and source links", credits),
    button(
      "Save project details",
      () =>
        api("save", {
          id: id.value,
          metadata: {
            author: author.value,
            license: license.value,
            description: desc.value,
            credits: credits.value,
          },
        }),
      true,
    ),
  );
  renderFields(host, "theme");
  const source = pathPicker("", "directory");
  host.append(
    group(
      "Start from another theme",
      source.node,
      row(
        button("Import folder", async () => {
          if (
            confirm(
              "Import into this project? The current theme is retained in the working folder’s imports directory.",
            )
          )
            await importTheme(source.input.value);
        }),
        button("Import theme ZIP…", async () => {
          const path = await pick("file", "Choose a single theme ZIP");
          if (path && confirm("Import this pack and retain its licenses?"))
            await importTheme(path);
        }),
      ),
      el("small", {
        class: "help",
        text: "Import duplicates the pack into your project; the original is untouched. This resets edit undo history.",
      }),
    ),
  );
  const licenseFile = button("Add a full license / credits file…", async () => {
    const file = await upload(".txt,.md,.license");
    if (file)
      await api("upload", {
        path: "notices/" + file.name.replace(/[^a-zA-Z0-9_.-]/g, "_"),
        data: await fileData(file),
        name: file.name,
      });
  });
  host.append(licenseFile);
}
async function extractPalette() {
  const file = await upload("image/*");
  if (!file) return;
  const image = await loadImage(await fileData(file));
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const ctx = c.getContext("2d");
  ctx.drawImage(image, 0, 0, 64, 64);
  const pixels = ctx.getImageData(0, 0, 64, 64).data,
    colors = new Map();
  for (let i = 0; i < pixels.length; i += 4) {
    if (pixels[i + 3] < 128) continue;
    const color =
      "#" +
      [pixels[i], pixels[i + 1], pixels[i + 2]]
        .map((v) =>
          Math.min(255, Math.round(v / 24) * 24)
            .toString(16)
            .padStart(2, "0"),
        )
        .join("");
    colors.set(color, (colors.get(color) || 0) + 1);
  }
  const choices = [...colors].sort((a, b) => b[1] - a[1]).slice(0, 12);
  const groupNode = group("Extracted colors — choose a role");
  for (const [color] of choices) {
    const role = select(Object.keys(state.schema.colors), "accent");
    groupNode.append(
      el(
        "div",
        { class: "input-row" },
        el("input", { type: "color", value: color }),
        role,
        button(color, () =>
          api("field", { section: "colors", key: role.value, value: color }),
        ),
      ),
    );
  }
  $("inspector-content").prepend(groupNode);
}
function backgroundInspector(host) {
  const slots = [
    ["top", "Top wallpaper"],
    ["bottom", "Bottom wallpaper"],
    ["top_surface", "Top reading surface"],
    ["bottom_surface", "Bottom reading surface"],
  ];
  for (const [key, label] of slots) {
    const path =
      state.config.backgrounds?.[key] || "backgrounds/" + key + ".png";
    host.append(
      group(
        label,
        assetThumb(path),
        row(
          button("Edit / draw", () =>
            editAsset(path, 256, 192, { section: "backgrounds", key }),
          ),
          button("Import image…", () =>
            importImage(path, 256, 192, "backgrounds", key),
          ),
          button("Generate material", () =>
            materialInspector(path, 256, 192, "backgrounds", key),
          ),
        ),
      ),
    );
  }
  renderFields(host, "backgrounds");
}
function assetThumb(path) {
  const found = state.assets.find((a) => a.path === path);
  return found
    ? el("img", { src: assetUrl(path), class: "texture-preview", alt: path })
    : el("p", {
        class: "help",
        text: "No asset. Built-in fallback remains available.",
      });
}
function spriteInspector(host, kind) {
  const directory = state.config[kind]?.directory || kind,
    names = state[kind];
  host.append(
    row(
      button("Fill missing slots", () =>
        api("generate", {
          kind,
          options: { style: kind === "components" ? "linen" : "soft" },
        }),
      ),
      button("Generate set…", () => generatorInspector(kind)),
      button("Import atlas…", () => atlasInspector(kind)),
      button("Export atlas", () => exportAtlas(kind)),
    ),
  );
  const grid = el("div", { class: "slot-grid" });
  for (const name of names) {
    const path = directory + "/" + name + ".png",
      exists = state.assets.some((a) => a.path === path),
      slot = el("button", {
        class:
          "slot " +
          (exists ? "" : "missing ") +
          (selectedSlot === path ? "active" : ""),
        title: path,
        onclick: () =>
          guard(async () => {
            await editAsset(path, 32, 32, {
              section: kind,
              key: "directory",
              value: directory,
            });
            selectedSlot = path;
            inspect();
          }),
      });
    slot.append(
      exists
        ? el("img", { src: assetUrl(path), alt: "" })
        : el("div", { style: "height:37px;font-size:22px", text: "+" }),
      el("span", { text: name }),
    );
    grid.append(slot);
  }
  host.append(
    grid,
    group(
      "Selected asset",
      el("div", { class: "mono", text: selectedSlot }),
      row(
        button("Import image…", () =>
          importImage(selectedSlot, 32, 32, kind, "directory", null, directory),
        ),
        button("Material recipe", () =>
          materialInspector(selectedSlot, 32, 32, kind, "directory", directory),
        ),
        button("Copy to slots…", () => copySlots(selectedSlot)),
        button("Remove", async () => {
          if (confirm("Remove " + selectedSlot + "?"))
            await api("remove", { path: selectedSlot });
        }),
      ),
    ),
  );
  renderFields(host, kind);
}
function generatorInspector(kind) {
  const host = $("inspector-content"),
    style = select(
      kind === "icons"
        ? ["soft", "pixel"]
        : ["paper", "linen", "glass", "metal", "wood", "flat", "gradient"],
      kind === "icons" ? "soft" : "paper",
    );
  host.prepend(
    group(
      "Starter set recipe",
      style,
      note(
        "Starter shapes are editable. Generating all slots replaces only missing files unless replacement is checked.",
      ),
      (() => {
        const replace = el("input", { type: "checkbox" });
        return el(
          "div",
          {},
          el("label", {}, replace, " Replace existing slots"),
          row(
            button(
              "Generate",
              () =>
                api("generate", {
                  kind,
                  options: { style: style.value, replace: replace.checked },
                }),
              true,
            ),
          ),
        );
      })(),
    ),
  );
}
function atlasInspector(kind) {
  const host = $("inspector-content"),
    [cf, c] = number("Columns", 8, 1, 16),
    [rf, r] = number("Rows", 4, 1, 16);
  host.prepend(
    group(
      "Import sprite sheet",
      note(
        "Tiles map left-to-right, top-to-bottom in the slot order above. Imported tiles are fitted to 32×32.",
      ),
      cf,
      rf,
      button(
        "Choose atlas…",
        async () => {
          const file = await upload("image/png");
          if (file)
            await api("atlas", {
              kind,
              columns: Number(c.value),
              rows: Number(r.value),
              data: await fileData(file),
            });
        },
        true,
      ),
    ),
  );
}
async function exportAtlas(kind) {
  const names = state[kind],
    dir = state.config[kind]?.directory || kind,
    c = document.createElement("canvas");
  c.width = 8 * 32;
  c.height = Math.ceil(names.length / 8) * 32;
  const ctx = c.getContext("2d");
  for (let i = 0; i < names.length; i++) {
    const path = dir + "/" + names[i] + ".png";
    if (image) {
      ctx.drawImage(image, (i % 8) * 32, Math.floor(i / 8) * 32, 32, 32);
    }
  }
  const link = el("a", {
    href: c.toDataURL("image/png"),
    download: kind + "-atlas.png",
  });
  link.click();
}
function materialInspector(
  path,
  width,
  height,
  bindSection = null,
  key = null,
  bindingValue = null,
) {
  const host = $("inspector-content"),
    style = select(
      ["paper", "linen", "glass", "metal", "wood", "flat", "gradient"],
      "paper",
    ),
    color = el("input", {
      type: "color",
      value: state.config.colors?.surface || "#e8dcc5",
    }),
    edge = el("input", {
      type: "color",
      value: state.config.colors?.line || "#84664a",
    });
  const fields = [
    ["Opacity", 255, 0, 255],
    ["Grain", 8, 0, 30],
    ["Radius", 5, 0, 128],
    ["Border", 1, 0, 12],
    ["Seed", 17, 0, 99999],
  ].map(([n, v, a, b]) => [n, ...number(n, v, a, b)]);
  host.prepend(
    group(
      "Material recipe",
      field("Surface", style),
      field("Base color", color),
      field("Edge color", edge),
      ...fields.map((f) => f[1]),
      button(
        "Generate " + width + "×" + height,
        async () => {
          const values = Object.fromEntries(
            fields.map(([name, _, input]) => [
              name.toLowerCase(),
              Number(input.value),
            ]),
          );
          await api("material", {
            path,
            binding: bindSection
              ? { section: bindSection, key, value: bindingValue ?? path }
              : null,
            options: {
              style: style.value,
              color: color.value,
              edge: edge.value,
              width,
              height,
              ...values,
            },
          });
          await editAsset(
            path,
            width,
            height,
            bindSection
              ? { section: bindSection, key, value: bindingValue ?? path }
              : null,
          );
        },
        true,
      ),
      note(
        "Recipes are baked offline. Components quantize alpha to 0 / 85 / 170 / 255; material shade maps must be opaque.",
      ),
    ),
  );
}
async function importImage(
  path,
  width,
  height,
  bindSection = null,
  key = null,
  droppedFile = null,
  bindingValue = null,
) {
  const file = droppedFile || (await upload("image/*"));
  if (!file) return;
  const data = await fileData(file),
    host = $("inspector-content"),
    fit = select(["contain", "cover", "stretch", "native"], "cover"),
    sampling = select(["smooth", "nearest"], "smooth"),
    [op, o] = number("Opacity %", 100, 0, 100),
    [ax, x] = number("Crop anchor X", 0.5, 0, 1, 0.05),
    [ay, y] = number("Crop anchor Y", 0.5, 0, 1, 0.05);
  host.prepend(
    group(
      "Import " + file.name,
      el("img", { class: "texture-preview", src: data, alt: "Source artwork" }),
      field("Fit", fit),
      field("Sampling", sampling),
      op,
      ax,
      ay,
      button(
        "Convert and assign",
        async () => {
          await api("image", {
            path,
            data,
            binding: bindSection
              ? { section: bindSection, key, value: bindingValue ?? path }
              : null,
            options: {
              width,
              height,
              fit: fit.value,
              sampling: sampling.value,
              opacity: Number(o.value),
              anchor_x: Number(x.value),
              anchor_y: Number(y.value),
              source_name: file.name,
            },
          });
          await editAsset(
            path,
            width,
            height,
            bindSection
              ? { section: bindSection, key, value: bindingValue ?? path }
              : null,
          );
        },
        true,
      ),
    ),
  );
}
async function copySlots(source = activeAsset) {
  const text = prompt(
    "Destination theme-relative PNG paths, separated by commas:",
    source,
  );
  if (text)
    await api("copy", {
      source,
      targets: text
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean),
    });
}
function fontInspector(host) {
  renderFields(host, "fonts");
  const role = select(["ui", "heading"], fontRole),
    [sf, size] = number("Font size", 10, 5, 24),
    [bf, baseline] = number("Baseline", 10, 0, 20),
    [hf, height] = number("Heading line height", 16, 12, 16),
    [ef, edge] = number("Allowed vertical bearing shift", 0, 0, 2),
    weight = el("input", { placeholder: "Optional variable font weight" });
  role.onchange = () => {
    fontRole = role.value;
    height.disabled = role.value === "ui";
  };
  height.disabled = role.value === "ui";
  host.append(
    group(
      "Convert TTF / OTF",
      field("Role", role),
      sf,
      bf,
      hf,
      ef,
      field("Weight axis", weight),
      button(
        "Choose source font and convert…",
        async () => {
          const file = await upload(".ttf,.otf");
          if (file)
            await api("font", {
              role: role.value,
              name: file.name,
              data: await fileData(file),
              options: {
                size: Number(size.value),
                baseline: Number(baseline.value),
                height: Number(height.value),
                edge_shift: Number(edge.value),
                weight: weight.value,
                latin1: true,
              },
            });
        },
        true,
      ),
      button("Import prepared DSFONT…", async () => {
        const file = await upload(".dsfont");
        if (!file) return;
        const path = "fonts/" + role.value + ".dsfont";
        await api("upload", {
          path,
          data: await fileData(file),
          name: file.name,
          format: "font",
          heading: role.value === "heading",
          binding: { section: "fonts", key: role.value },
        });
      }),
      note(
        "Overflow is rejected, never cropped. Body height stays 12 px; headings use 12–16 px. Add the complete source-font license under Project. Authoring text preview is approximate; use the native renderer for final typography.",
      ),
    ),
  );
}
function audioInspector(host) {
  const role = select(["music", "cursor", "confirm", "back"], audioRole),
    rate = select(
      ["8000", "12000", "16000", "22050", "24000", "32000", "44100", "48000"],
      "16000",
    );
  const inputs = [
    ["Start seconds", 0, 0, 36000, 0.1],
    ["Length seconds", audioRole === "music" ? 12 : 0.5, 0.01, 65, 0.1],
    ["Gain", 1, 0, 4, 0.05],
    ["Edge fade seconds", 0.05, 0, 5, 0.01],
    ["Loop crossfade seconds", 0, 0, 5, 0.05],
  ].map(([n, v, a, b, s]) => [n, ...number(n, v, a, b, s)]);
  const updateCap = () => {
    const limit =
      (role.value === "music" ? 1048576 : 65536) / (Number(rate.value) * 2);
    const input = inputs[1][2];
    input.max = String(limit);
    input.value = String(
      Math.min(Number(input.value), Math.floor(limit * 100) / 100),
    );
  };
  role.onchange = () => {
    audioRole = role.value;
    inputs[1][2].value = role.value === "music" ? "12" : "0.5";
    updateCap();
  };
  rate.onchange = updateCap;
  updateCap();
  host.append(
    group(
      "Prepare recording",
      field("Role", role),
      field("Output rate", rate),
      ...inputs.map((v) => v[1]),
      button(
        "Choose audio and convert…",
        async () => {
          const file = await upload(".wav,.mp3,.ogg,.flac,.m4a");
          if (!file) return;
          const vals = inputs.map((v) => Number(v[2].value));
          await api("audio", {
            role: role.value,
            name: file.name,
            data: await fileData(file),
            options: {
              rate: Number(rate.value),
              start: vals[0],
              seconds: vals[1],
              gain: vals[2],
              fade: vals[3],
              loop: vals[4],
            },
          });
        },
        true,
      ),
      note(
        "Music PCM ≤1 MiB; each cue ≤64 KiB. WAV PCM conversion works directly. " +
          (state.ffmpeg
            ? "FFmpeg is available for other formats."
            : "Install FFmpeg on PATH for MP3 / OGG / FLAC / M4A conversion."),
      ),
    ),
  );
  for (const [key, path] of Object.entries(state.config.audio || {}))
    host.append(
      group(
        key,
        el("audio", {
          controls: true,
          src: assetUrl(path),
          class: "audio-preview",
        }),
      ),
    );
  renderFields(host, "audio");
}
function motionInspector(host) {
  host.append(
    note(
      "The header accent is limited to eight 32×32 frames, displayed at 16×16. It never becomes a full-screen animation.",
    ),
  );
  const [cf, count] = number("Prepared frames", 8, 1, 8);
  host.append(
    cf,
    button(
      "Import animated GIF / still…",
      async () => {
        const file = await upload("image/gif,image/png");
        if (file)
          await api("ambient", {
            data: await fileData(file),
            name: file.name,
            count: Number(count.value),
          });
      },
      true,
    ),
  );
  renderFields(host, "motion");
}
function splashInspector(host) {
  const file = state.assets.find((a) => a.path === "splash.gsp");
  host.append(
    note(
      "The splash has its own editable project in this working folder’s splash/ directory. Top and bottom layers, GIFs, frame sequences, scale, motion, timing, opacity and audio use the existing designer.",
    ),
    button(
      state.splash_running ? "Splash designer is open" : "Open splash designer",
      () => api("splash-open"),
      true,
    ),
    row(
      button("Build saved splash into theme", async () => {
        const bytes = await api("splash-build");
        toast("Built splash.gsp · " + bytes.toLocaleString() + " bytes");
      }),
      button("Import prepared .gsp…", async () => {
        const f = await upload(".gsp");
        if (f)
          await api("upload", {
            path: "splash.gsp",
            data: await fileData(f),
            name: f.name,
          });
      }),
    ),
    el("p", {
      class: "help",
      text: file
        ? "Included splash: " + file.bytes.toLocaleString() + " bytes"
        : "No theme splash yet. Gloam’s normal fallback applies.",
    }),
    button("Open splash working folder", () =>
      api("open-folder", { path: "splash" }),
    ),
    button("Remove theme splash", async () => {
      if (confirm("Remove the prepared splash? The editable project stays."))
        await api("remove", { path: "splash.gsp" });
    }),
  );
}
function publishInspector(host) {
  const report = state.report;
  host.append(
    note(
      report.valid
        ? "No blocking format errors. Console testing is still required."
        : "Fix the errors below before exporting.",
    ),
    el(
      "dl",
      { class: "metrics" },
      el("dt", { text: "Manifest" }),
      el("dd", { text: report.manifest_bytes + " / 4,096 bytes" }),
      el("dt", { text: "Referenced assets" }),
      el("dd", { text: (report.total_bytes / 1024).toFixed(1) + " KiB" }),
    ),
  );
  for (const error of report.errors)
    host.append(el("p", { class: "log-error", text: error }));
  for (const warning of report.warnings)
    host.append(el("p", { class: "help", text: warning }));
  host.append(
    row(
      button("Prepare assets.gfx", async () => {
        const n = await api("prepare");
        toast("Prepared " + n.toLocaleString() + " bytes");
      }),
      button("Export runtime ZIP", exportTheme, true),
    ),
    button("Open exports folder", () =>
      api("open-folder", { path: "exports" }),
    ),
  );
  const sd = pathPicker(installRoot),
    replace = el("input", { type: "checkbox" });
  host.append(
    group(
      "Install theme on SD",
      sd.node,
      el("label", {}, replace, " Replace existing theme (backup on PC)"),
      button(
        "Install this theme",
        async () => {
          if (
            confirm(
              "Install " +
                state.id +
                " in the selected SD/staging folder? Gloam settings are unchanged.",
            )
          ) {
            const path = await api("install", {
              path: sd.input.value,
              replace: replace.checked,
            });
            toast("Installed " + path);
          }
        },
        true,
      ),
      el("small", {
        class: "help",
        text: "Only this theme folder is changed. Replacement backups stay in this project’s exports/backups folder.",
      }),
    ),
  );
  sd.input.oninput = () => {
    installRoot = sd.input.value;
  };
  const native = pathPicker(nativeExecutable, "file");
  native.input.oninput = () => {
    nativeExecutable = native.input.value;
  };
  host.append(
    group(
      "Native renderer check",
      native.node,
      button("Render with local Gloam host tool", async () => {
        const file = await api("native", {
          executable: native.input.value,
          sample: $("sample").value,
        });
        clearTimeout(previewTimer);
        document.querySelector(".caption").textContent =
          "Native Gloam renderer · synthetic library";
        $("preview").src = url("/api/export-file", { path: file });
        setStage("preview");
        toast("Native renderer output loaded");
      }),
      el("small", {
        class: "help",
        text: "Optional trusted build/host/preview executable from Gloam. Uses a synthetic SD fixture. No compiler is required for ordinary theme export.",
      }),
    ),
  );
}
async function exportTheme() {
  const file = await api("export");
  log("Exported " + file);
  toast("Theme ZIP exported");
  const link = el("a", {
    href: url("/api/export-file", { path: state.id + ".zip" }),
    download: state.id + ".zip",
  });
  link.click();
}
function renderAssets() {
  if (!state) return;
  const filter = $("asset-search").value.toLowerCase(),
    grid = $("asset-grid");
  grid.replaceChildren();
  for (const item of state.assets.filter((a) =>
    a.path.toLowerCase().includes(filter),
  )) {
    const image = /\.(png|jpe?g|gif)$/i.test(item.path);
    const b = el("button", {
      class: "asset-tile",
      onclick: () =>
        guard(async () => {
          if (image) {
            await editAsset(item.path, item.width || 32, item.height || 32);
          } else {
            toast(item.path + " · " + item.bytes.toLocaleString() + " bytes");
          }
        }),
    });
    if (image)
      b.append(
        el("img", { src: assetUrl(item.path), alt: "", loading: "lazy" }),
      );
    else
      b.append(
        el("div", {
          style: "height:85px;display:grid;place-items:center;font-size:26px",
          text: item.path.endsWith(".wav") ? "♫" : "≡",
        }),
      );
    b.append(
      el("span", { text: item.path }),
      el("span", {
        text:
          (item.bytes / 1024).toFixed(1) +
          " KiB" +
          (item.width ? " · " + item.width + "×" + item.height : ""),
      }),
    );
    grid.append(b);
  }
}
function canvas(width = artWidth, height = artHeight) {
  const c = document.createElement("canvas");
  c.width = width;
  c.height = height;
  return c;
}
function snapshotPaint() {
  return {
    layers: layers.map((l) => ({
      name: l.name,
      visible: l.visible,
      opacity: l.opacity,
      blend: l.blend,
      data: l.canvas.toDataURL(),
    })),
    index: layerIndex,
    width: artWidth,
    height: artHeight,
  };
}
function checkpointPaint() {
  paintHistory.push(snapshotPaint());
  while (
    paintHistory.length > 30 ||
    (paintHistory.length > 1 &&
      paintHistory.reduce((n, s) => n + JSON.stringify(s).length, 0) >
        32 * 1024 * 1024)
  )
    paintHistory.shift();
  paintFuture = [];
  dirtyArt = true;
  saveStatus();
}
async function restorePaint(s) {
  artWidth = s.width;
  artHeight = s.height;
  layers = [];
  for (const l of s.layers) {
    const c = canvas();
    c.getContext("2d").drawImage(await loadImage(l.data), 0, 0);
    layers.push({ ...l, canvas: c });
  }
  layerIndex = Math.max(0, Math.min(layers.length - 1, s.index));
  dirtyArt = true;
  paintRender();
}
async function editAsset(path, width = 32, height = 32, binding = null) {
  await settleEdits(true, false);
  const doc = await api("artboard-load", { path }, false);
  let image = null;
  if (!doc && state.assets.some((a) => a.path === path))
    image = await loadImage(assetUrl(path));
  activeAsset = path;
  loadedAsset = path;
  assetBinding = binding;
  artWidth = width;
  artHeight = height;
  if (doc) {
    await restorePaint(doc);
    dirtyArt = false;
  } else {
    const c = canvas();
    if (image) {
      artWidth = image.naturalWidth;
      artHeight = image.naturalHeight;
      c.width = artWidth;
      c.height = artHeight;
      c.getContext("2d").drawImage(image, 0, 0);
    }
    layers = [
      {
        name: "Base",
        visible: true,
        opacity: 1,
        blend: "source-over",
        canvas: c,
      },
    ];
    layerIndex = 0;
  }
  paintHistory = [];
  paintFuture = [];
  dirtyArt = false;
  paintRender();
  setStage("canvas");
}
function composite() {
  const c = canvas();
  const ctx = c.getContext("2d");
  for (const layer of layers) {
    if (!layer.visible) continue;
    ctx.globalAlpha = layer.opacity;
    ctx.globalCompositeOperation = layer.blend;
    ctx.drawImage(layer.canvas, 0, 0);
  }
  return c;
}
function renderAssignment() {
  const select = $("asset-assignment");
  select.replaceChildren();
  const choices = [
    { label: "Current file path", path: activeAsset, binding: assetBinding },
  ];
  for (const key of [
    "top",
    "bottom",
    ...(artWidth === 256 && artHeight === 192
      ? ["top_surface", "bottom_surface"]
      : []),
  ]) {
    choices.push({
      label: "Background / " + key,
      path: state.config.backgrounds?.[key] || "backgrounds/" + key + ".png",
      binding: { section: "backgrounds", key },
    });
  }
  if (artWidth === 256 && artHeight === 192) {
    for (const key of ["material", "focus_material"])
      choices.push({
        label: "Components / " + key,
        path: state.config.components?.[key] || "components/" + key + ".png",
        binding: { section: "components", key },
      });
  }
  if (artWidth === 32 && artHeight === 32) {
    for (const kind of ["icons", "components"]) {
      const directory = state.config[kind]?.directory || kind;
      for (const name of state[kind])
        choices.push({
          label: kind + " / " + name,
          path: directory + "/" + name + ".png",
          binding: { section: kind, key: "directory", value: directory },
        });
    }
  }
  for (const [i, choice] of choices.entries())
    select.append(el("option", { text: choice.label, value: String(i) }));
  select.onchange = () => {
    const choice = choices[Number(select.value)];
    activeAsset = choice.path;
    assetBinding = choice.binding;
    dirtyArt = true;
    paintRender();
  };
}
function paintRender() {
  const c = $("paint");
  c.width = artWidth;
  c.height = artHeight;
  if (layers.length) c.getContext("2d").drawImage(composite(), 0, 0);
  const scale = Math.min(
    14,
    Math.max(1, Math.floor(500 / Math.max(artWidth, artHeight))),
  );
  c.style.width = artWidth * scale + "px";
  c.style.height = artHeight * scale + "px";
  $("paint-guides").width = artWidth * scale;
  $("paint-guides").height = artHeight * scale;
  drawGuides(scale);
  $("artboard-name").textContent =
    activeAsset +
    " · " +
    artWidth +
    "×" +
    artHeight +
    (dirtyArt ? " · unsaved" : "");
  $("artboard-name").classList.toggle("draft", dirtyArt);
  saveStatus();
  renderAssignment();
  const host = $("layer-list");
  host.replaceChildren();
  layers.forEach((l, i) => {
    const visible = el("input", {
        type: "checkbox",
        checked: l.visible,
        onchange: (e) => {
          checkpointPaint();
          l.visible = e.target.checked;
          paintRender();
        },
      }),
      opacity = el("input", {
        type: "range",
        min: 0,
        max: 100,
        value: l.opacity * 100,
        onchange: (e) => {
          checkpointPaint();
          l.opacity = Number(e.target.value) / 100;
          paintRender();
        },
      }),
      blend = select(["source-over", "multiply", "screen", "overlay"], l.blend);
    blend.onchange = () => {
      checkpointPaint();
      l.blend = blend.value;
      paintRender();
    };
    host.append(
      el(
        "div",
        { class: "layer " + (i === layerIndex ? "active" : "") },
        visible,
        button(l.name, () => {
          layerIndex = i;
          paintRender();
        }),
        opacity,
        blend,
      ),
    );
  });
}
function drawGuides(scale) {
  const g = $("paint-guides"),
    d = g.getContext("2d");
  d.clearRect(0, 0, g.width, g.height);
  if ($("pixel-grid").checked && scale >= 4) {
    d.strokeStyle = "#5555";
    d.lineWidth = 1;
    for (let x = 0; x <= artWidth; x++) {
      d.beginPath();
      d.moveTo(x * scale + 0.5, 0);
      d.lineTo(x * scale + 0.5, g.height);
      d.stroke();
    }
    for (let y = 0; y <= artHeight; y++) {
      d.beginPath();
      d.moveTo(0, y * scale + 0.5);
      d.lineTo(g.width, y * scale + 0.5);
      d.stroke();
    }
  }
  if ($("slice-grid").checked) {
    const b = Number(state.config.components?.border || 6) * scale;
    d.strokeStyle = "#ee53a4";
    for (const x of [b, g.width - b]) {
      d.beginPath();
      d.moveTo(x, 0);
      d.lineTo(x, g.height);
      d.stroke();
    }
    for (const y of [b, g.height - b]) {
      d.beginPath();
      d.moveTo(0, y);
      d.lineTo(g.width, y);
      d.stroke();
    }
  }
}
function point(event) {
  const r = $("paint").getBoundingClientRect();
  return [
    Math.max(
      0,
      Math.min(
        artWidth - 1,
        Math.floor(((event.clientX - r.left) * artWidth) / r.width),
      ),
    ),
    Math.max(
      0,
      Math.min(
        artHeight - 1,
        Math.floor(((event.clientY - r.top) * artHeight) / r.height),
      ),
    ),
  ];
}
let drawing = null;
function paintStyle(ctx) {
  ctx.globalAlpha = Number($("paint-alpha").value) / 255;
  ctx.globalCompositeOperation =
    $("paint-tool").value === "eraser" ? "destination-out" : "source-over";
  ctx.fillStyle = $("paint-color").value;
  ctx.strokeStyle = $("paint-color").value;
  ctx.lineWidth = Number($("brush-size").value);
  ctx.lineCap = "round";
}
function flood(ctx, x, y) {
  const image = ctx.getImageData(0, 0, artWidth, artHeight),
    data = image.data,
    start = (y * artWidth + x) * 4,
    color = $("paint-color").value,
    replace = [1, 3, 5]
      .map((n) => parseInt(color.slice(n, n + 2), 16))
      .concat(Number($("paint-alpha").value)),
    original = [...data.slice(start, start + 4)];
  if (original.every((v, i) => v === replace[i])) return;
  const stack = [y * artWidth + x],
    seen = new Uint8Array(artWidth * artHeight);
  while (stack.length) {
    const pos = stack.pop();
    if (seen[pos]) continue;
    seen[pos] = 1;
    const offset = pos * 4;
    if (!original.every((v, i) => data[offset + i] === v)) continue;
    data.set(replace, offset);
    const px = pos % artWidth,
      py = Math.floor(pos / artWidth);
    if (px > 0) stack.push(pos - 1);
    if (px < artWidth - 1) stack.push(pos + 1);
    if (py > 0) stack.push(pos - artWidth);
    if (py < artHeight - 1) stack.push(pos + artWidth);
  }
  ctx.putImageData(image, 0, 0);
}
$("paint").onpointerdown = (event) =>
  guard(async () => {
    if (!layers.length) return;
    const [x, y] = point(event),
      tool = $("paint-tool").value,
      ctx = layers[layerIndex].canvas.getContext("2d");
    if (tool === "eyedropper") {
      const p = $("paint").getContext("2d").getImageData(x, y, 1, 1).data;
      $("paint-color").value =
        "#" +
        [...p.slice(0, 3)].map((v) => v.toString(16).padStart(2, "0")).join("");
      $("paint-alpha").value = p[3];
      return;
    }
    checkpointPaint();
    drawing = {
      x,
      y,
      last: [x, y],
      backup: ctx.getImageData(0, 0, artWidth, artHeight),
      tool,
    };
    $("paint").setPointerCapture(event.pointerId);
    paintStyle(ctx);
    if (tool === "fill") {
      flood(ctx, x, y);
      drawing = null;
    } else if (tool === "text") {
      const value = prompt("Text for this layer:", "");
      if (value) {
        ctx.font =
          Math.max(6, Number($("brush-size").value) * 3) + "px sans-serif";
        ctx.fillText(value, x, y);
      }
      drawing = null;
    } else if (tool === "brush" || tool === "eraser") {
      ctx.fillRect(
        x,
        y,
        Number($("brush-size").value),
        Number($("brush-size").value),
      );
    }
    paintRender();
  });
$("paint").onpointermove = (event) => {
  if (!drawing) return;
  const [x, y] = point(event),
    ctx = layers[layerIndex].canvas.getContext("2d"),
    s = drawing;
  paintStyle(ctx);
  if (["brush", "eraser"].includes(s.tool)) {
    ctx.beginPath();
    ctx.moveTo(s.last[0] + 0.5, s.last[1] + 0.5);
    ctx.lineTo(x + 0.5, y + 0.5);
    ctx.stroke();
    s.last = [x, y];
  } else {
    ctx.putImageData(s.backup, 0, 0);
    if (s.tool === "move") {
      const temp = canvas();
      temp.getContext("2d").putImageData(s.backup, 0, 0);
      ctx.clearRect(0, 0, artWidth, artHeight);
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = "source-over";
      ctx.drawImage(temp, x - s.x, y - s.y);
    } else if (s.tool === "gradient") {
      const gradient = ctx.createLinearGradient(
        s.x,
        s.y,
        x === s.x ? x + 1 : x,
        y,
      );
      gradient.addColorStop(0, $("paint-color").value);
      gradient.addColorStop(1, "transparent");
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, artWidth, artHeight);
    } else {
      ctx.beginPath();
      if (s.tool === "line") {
        ctx.moveTo(s.x + 0.5, s.y + 0.5);
        ctx.lineTo(x + 0.5, y + 0.5);
      } else if (s.tool === "rectangle") {
        ctx.rect(s.x, s.y, x - s.x, y - s.y);
      } else if (s.tool === "ellipse") {
        ctx.ellipse(
          (s.x + x) / 2,
          (s.y + y) / 2,
          Math.abs(x - s.x) / 2,
          Math.abs(y - s.y) / 2,
          0,
          0,
          Math.PI * 2,
        );
      }
      if ($("shape-fill").checked && s.tool !== "line") ctx.fill();
      else ctx.stroke();
    }
  }
  paintRender();
};
$("paint").onpointerup = $("paint").onpointercancel = () => {
  drawing = null;
};
$("paint-undo").onclick = () =>
  guard(async () => {
    if (paintHistory.length) {
      paintFuture.push(snapshotPaint());
      await restorePaint(paintHistory.pop());
    }
  });
$("paint-redo").onclick = () =>
  guard(async () => {
    if (paintFuture.length) {
      paintHistory.push(snapshotPaint());
      await restorePaint(paintFuture.pop());
    }
  });
async function saveArtwork() {
  if (!layers.length) return;
  if (
    activeAsset !== loadedAsset &&
    state.assets.some((a) => a.path === activeAsset) &&
    !confirm("Replace existing artwork at " + activeAsset + "?")
  )
    throw new CanceledEdit();
  await api("artboard-save", {
    path: activeAsset,
    binding: assetBinding,
    data: composite().toDataURL("image/png"),
    document: snapshotPaint(),
  });
  dirtyArt = false;
  loadedAsset = activeAsset;
  paintRender();
  toast("Artwork and editable layers saved");
}
$("commit-art").onclick = () => guard(saveArtwork);
$("add-layer").onclick = () =>
  guard(() => {
    if (layers.length >= 16) throw Error("Use at most 16 layers per artboard.");
    checkpointPaint();
    layers.push({
      name: prompt("Layer name:", "Layer " + (layers.length + 1)) || "Layer",
      visible: true,
      opacity: 1,
      blend: "source-over",
      canvas: canvas(),
    });
    layerIndex = layers.length - 1;
    paintRender();
  });
async function importLayer(droppedFile = null) {
  if (layers.length >= 16) throw Error("Use at most 16 layers.");
  const file = droppedFile || (await upload("image/*"));
  if (!file) return;
  const image = await loadImage(await fileData(file));
  checkpointPaint();
  const c = canvas();
  const scale = Math.min(artWidth / image.width, artHeight / image.height);
  c.getContext("2d").drawImage(
    image,
    0,
    0,
    image.width * scale,
    image.height * scale,
  );
  layers.push({
    name: file.name,
    visible: true,
    opacity: 1,
    blend: "source-over",
    canvas: c,
  });
  layerIndex = layers.length - 1;
  paintRender();
}
$("import-layer").onclick = () => guard(() => importLayer());
window.addEventListener("dragover", (event) => event.preventDefault());
window.addEventListener("drop", (event) => {
  event.preventDefault();
  guard(async () => {
    const file = event.dataTransfer.files[0];
    if (!file) return;
    if (!file.type.startsWith("image/"))
      throw Error(
        "Drop an image here. Use the audio/font/splash importers for other assets.",
      );
    if (activeStage === "canvas" && layers.length) await importLayer(file);
    else {
      const asset = state.assets.find((a) => a.path === activeAsset);
      await importImage(
        activeAsset,
        asset?.width || 32,
        asset?.height || 32,
        null,
        null,
        file,
      );
      toast("Choose fit and crop options in the inspector.");
    }
  });
});
$("duplicate-layer").onclick = () =>
  guard(() => {
    if (!layers.length || layers.length >= 16) return;
    checkpointPaint();
    const c = canvas();
    c.getContext("2d").drawImage(layers[layerIndex].canvas, 0, 0);
    layers.splice(layerIndex + 1, 0, {
      ...layers[layerIndex],
      name: layers[layerIndex].name + " copy",
      canvas: c,
    });
    layerIndex++;
    paintRender();
  });
function moveLayer(delta) {
  const target = layerIndex + delta;
  if (target < 0 || target >= layers.length) return;
  checkpointPaint();
  [layers[target], layers[layerIndex]] = [layers[layerIndex], layers[target]];
  layerIndex = target;
  paintRender();
}
$("new-canvas").onclick = () =>
  guard(async () => {
    const path = prompt("Theme-relative PNG path:", "artwork/new.png");
    if (!path) return;
    const value = prompt(
      "Canvas size (width × height, up to 512):",
      "256 x 192",
    );
    if (!value) return;
    const match = value.match(/^(\d+)\s*[x×, ]\s*(\d+)$/);
    if (!match) throw Error("Use width x height.");
    const w = Number(match[1]),
      h = Number(match[2]);
    if (w < 1 || w > 512 || h < 1 || h > 512)
      throw Error("Dimensions must be 1–512.");
    await editAsset(path, w, h);
  });
$("resize-canvas").onclick = () =>
  guard(() => {
    if (!layers.length) return;
    const value = prompt(
      "New size (resamples every layer):",
      artWidth + " x " + artHeight,
    );
    if (!value) return;
    const match = value.match(/^(\d+)\s*[x×, ]\s*(\d+)$/);
    if (!match) throw Error("Use width x height.");
    const w = Number(match[1]),
      h = Number(match[2]);
    if (w < 1 || w > 512 || h < 1 || h > 512)
      throw Error("Dimensions must be 1–512.");
    checkpointPaint();
    for (const layer of layers) {
      const c = canvas(w, h);
      c.getContext("2d").imageSmoothingEnabled = !$("pixel-grid").checked;
      c.getContext("2d").drawImage(layer.canvas, 0, 0, w, h);
      layer.canvas = c;
    }
    artWidth = w;
    artHeight = h;
    paintRender();
  });
function transformLayer(rotate) {
  if (!layers.length) return;
  checkpointPaint();
  const c = canvas(),
    ctx = c.getContext("2d");
  ctx.translate(artWidth / 2, artHeight / 2);
  if (rotate) ctx.rotate(Math.PI / 2);
  else ctx.scale(-1, 1);
  ctx.drawImage(layers[layerIndex].canvas, -artWidth / 2, -artHeight / 2);
  layers[layerIndex].canvas = c;
  paintRender();
}
$("rotate-layer").onclick = () => transformLayer(true);
$("flip-layer").onclick = () => transformLayer(false);
$("coverage-layer").onclick = () => {
  if (!layers.length) return;
  checkpointPaint();
  const ctx = layers[layerIndex].canvas.getContext("2d"),
    image = ctx.getImageData(0, 0, artWidth, artHeight);
  for (let i = 3; i < image.data.length; i += 4)
    image.data[i] = Math.round(image.data[i] / 85) * 85;
  ctx.putImageData(image, 0, 0);
  paintRender();
};
$("download-art").onclick = () => {
  if (layers.length)
    el("a", {
      href: composite().toDataURL("image/png"),
      download: activeAsset.split("/").pop(),
    }).click();
};
$("up-layer").onclick = () => moveLayer(1);
$("down-layer").onclick = () => moveLayer(-1);
$("delete-layer").onclick = () => {
  if (layers.length <= 1) return;
  checkpointPaint();
  layers.splice(layerIndex, 1);
  layerIndex = Math.min(layerIndex, layers.length - 1);
  paintRender();
};
for (const name of ["pixel-grid", "slice-grid"])
  $(name).onchange = () => paintRender();
$("undo").onclick = () => guard(() => api("undo"));
$("redo").onclick = () => guard(() => api("redo"));
async function saveProject() {
  document.activeElement.blur();
  if (dirtyArt) await saveArtwork();
  await saveManifest();
  await api("save");
  toast("Project saved in " + state.workspace);
}
$("save").onclick = () => guard(saveProject);
$("validate").onclick = () =>
  guard(async () => {
    await api("state");
    state.report.errors.forEach((t) => log(t, "error"));
    state.report.warnings.forEach((t) => log(t, "warning"));
    if (state.report.valid) log("No blocking format errors.");
    selectSection("publish");
  });
$("export").onclick = () => guard(exportTheme);
$("open-project").onclick = () =>
  guard(async () => {
    const path = await pick(
      "directory",
      "Create or reopen a Theme Studio working folder",
    );
    if (path) {
      await api("workspace", { path, create: true });
      layers = [];
      dirtyArt = false;
      setStage("preview");
      selectSection("project");
    }
  });
$("open-folder").onclick = () => guard(() => api("open-folder", { path: "." }));
$("reload-project").onclick = () =>
  guard(async () => {
    await api("workspace", { path: state.workspace });
    rawDraft = null;
    layers = [];
    dirtyArt = false;
    assetBinding = null;
    setStage("preview");
    selectSection("project");
    saveStatus();
  });
$("toggle-log").onclick = () =>
  document.querySelector(".activity").classList.toggle("open");
$("asset-search").oninput = renderAssets;
$("zoom").onchange = () => {
  const stage = $("preview-stage");
  const scale =
    $("zoom").value === "fit"
      ? Math.max(
          0.5,
          Math.min(
            3,
            (stage.clientWidth - 70) / 256,
            (stage.clientHeight - 160) / 396,
          ),
        )
      : Number($("zoom").value);
  $("preview").width = Math.round(256 * scale);
  $("preview").style.width = $("preview").width + "px";
};
for (const id of ["sample", "preview-view", "selected", "guides"])
  $(id).onchange = refreshPreview;
document
  .querySelectorAll("[data-stage]")
  .forEach((b) => (b.onclick = () => setStage(b.dataset.stage)));
for (const [id, icon, label] of sections)
  $("navigation").append(
    el(
      "button",
      {
        "data-section": id,
        class: id === section ? "active" : "",
        onclick: () => selectSection(id),
      },
      el("span", { class: "nav-icon", text: icon }),
      label,
    ),
  );
window.addEventListener("resize", () => $("zoom").onchange());
window.addEventListener("beforeunload", (e) => {
  if (dirtyArt || rawDraft !== null) {
    e.preventDefault();
    e.returnValue = "";
  }
});
window.addEventListener("keydown", (e) => {
  if (!(e.ctrlKey || e.metaKey)) return;
  const editing = ["INPUT", "TEXTAREA"].includes(
    document.activeElement.tagName,
  );
  if (e.key.toLowerCase() === "s") {
    e.preventDefault();
    guard(saveProject);
  }
  if (e.key.toLowerCase() === "z" && !editing) {
    e.preventDefault();
    if (activeStage === "canvas" && layers.length) {
      const source = e.shiftKey ? paintFuture : paintHistory;
      const destination = e.shiftKey ? paintHistory : paintFuture;
      if (source.length) {
        destination.push(snapshotPaint());
        guard(() => restorePaint(source.pop()));
      }
    } else guard(() => api(e.shiftKey ? "redo" : "undo"));
  }
});
let coverDrag = null;
$("preview").onpointerdown = (e) => {
  if (
    section !== "layout" ||
    !$("guides").checked ||
    state.config.layout?.top_layout !== "scene"
  )
    return;
  const rect = e.target.getBoundingClientRect(),
    x = ((e.clientX - rect.left) * 256) / rect.width,
    y = ((e.clientY - rect.top) * 396) / rect.height;
  if (y < 118) {
    coverDrag = {
      x,
      y,
      ox: Number(state.config.layout.scene_cover_x || 18),
      oy: Number(state.config.layout.scene_cover_y || 34),
    };
    e.target.setPointerCapture(e.pointerId);
  }
};
$("preview").onpointerup = (e) =>
  guard(async () => {
    if (!coverDrag) return;
    const rect = e.target.getBoundingClientRect(),
      x = ((e.clientX - rect.left) * 256) / rect.width,
      y = ((e.clientY - rect.top) * 396) / rect.height,
      drag = coverDrag;
    coverDrag = null;
    const w = Number(state.config.layout.scene_cover_width || 48),
      h = Number(state.config.layout.scene_cover_height || 72);
    await api(
      "field",
      {
        section: "layout",
        key: "scene_cover_x",
        value: String(
          Math.max(2, Math.min(254 - w, Math.round(drag.ox + x - drag.x))),
        ),
      },
      false,
    );
    await api("field", {
      section: "layout",
      key: "scene_cover_y",
      value: String(
        Math.max(26, Math.min(116 - h, Math.round(drag.oy + y - drag.y))),
      ),
    });
  });
guard(async () => {
  const response = await fetch(url("/api/state"));
  if (!response.ok) throw Error("Could not open the project.");
  state = await response.json();
  updateShell();
  inspect();
  refreshPreview();
  renderAssets();
  $("zoom").onchange();
  log(
    "Project opened. Theme fields save on change; artwork saves with Save artwork.",
  );
});
