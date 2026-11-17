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
let navigationHistory = [],
  navigationRestoring = false,
  navigationEpoch = 0,
  backInFlight = false,
  canvasNeedsReload = false,
  previewScale = 1;
function captureNavigation() {
  return {
    section,
    stage: activeStage,
    asset: activeAsset,
    binding: assetBinding,
    width: artWidth,
    height: artHeight,
    slot: selectedSlot,
    inspectorScroll: document.querySelector(".inspector").scrollTop,
    stageScroll: $(activeStage + "-stage").scrollTop,
    preview: {
      sample: $("sample").value,
      view: $("preview-view").value,
      selected: $("selected").value,
      guides: $("guides").checked,
      zoom: $("zoom").value,
      left: $("preview-viewport").scrollLeft,
      top: $("preview-viewport").scrollTop,
    },
  };
}
function rememberNavigation(previous = captureNavigation()) {
  if (navigationRestoring) return;
  navigationEpoch++;
  navigationHistory.push(previous);
  if (navigationHistory.length > 40) navigationHistory.shift();
}
function stopMedia() {
  document
    .querySelectorAll("img[data-motion-demo]")
    .forEach((image) => image.stopMotion?.());
  document.querySelectorAll("audio,video").forEach((media) => media.pause());
}
function closeTool(panel) {
  panel.remove();
  navigationEpoch++;
  stopMedia();
  document.querySelector(".inspector").scrollTop = panel.returnScroll || 0;
  (panel.returnFocus?.isConnected ? panel.returnFocus : $("view-back")).focus({
    preventScroll: true,
  });
}
function toolGroup(title, ...children) {
  const panel = group(title, ...children);
  panel.dataset.transientTool = "true";
  panel.returnFocus = document.activeElement;
  panel.returnScroll = document.querySelector(".inspector").scrollTop;
  panel.prepend(button("Close " + title.toLowerCase(), () => closeTool(panel)));
  return panel;
}
async function goBack() {
  if (backInFlight) return;
  backInFlight = true;
  $("view-back").disabled = true;
  try {
    await returnToPreviousView();
  } finally {
    backInFlight = false;
    $("view-back").disabled = false;
  }
}
async function returnToPreviousView() {
  const tool = document.querySelector("[data-transient-tool]");
  if (tool) {
    closeTool(tool);
    return;
  }
  await settleEdits(true, true);
  const target = navigationHistory.at(-1) || {
    section: "project",
    stage: "preview",
    slot: "icons/folder.png",
  };
  stopMedia();
  navigationEpoch++;
  navigationRestoring = true;
  try {
    if (
      target.stage === "canvas" &&
      !(target.asset === activeAsset && layers.length && !canvasNeedsReload)
    )
      await editAsset(
        target.asset,
        target.width,
        target.height,
        target.binding,
      );
    section = target.section;
    selectedSlot = target.slot;
    setStage(target.stage, false);
    inspect();
    if (target.preview) {
      $("sample").value = target.preview.sample;
      $("preview-view").value = target.preview.view;
      $("selected").value = target.preview.selected;
      $("guides").checked = target.preview.guides;
      $("zoom").value = target.preview.zoom;
      $("zoom").onchange();
      $("preview-viewport").scrollLeft = target.preview.left || 0;
      $("preview-viewport").scrollTop = target.preview.top || 0;
    }
    document
      .querySelectorAll("[data-section]")
      .forEach((b) =>
        b.classList.toggle("active", b.dataset.section === section),
      );
    $("native-preview-back").classList.add("hidden");
    refreshPreview();
    if (navigationHistory.length) navigationHistory.pop();
    document.querySelector(".inspector").scrollTop =
      target.inspectorScroll || 0;
    $(target.stage + "-stage").scrollTop = target.stageScroll || 0;
  } finally {
    navigationRestoring = false;
  }
}
let controlId = 0;
let pending = Promise.resolve(),
  pendingCount = 0,
  dirtyArt = false,
  paintHistory = [],
  paintFuture = [],
  paintHistoryQueue = Promise.resolve(),
  paintHistoryBusy = false,
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
    "Header accent & selection feedback",
    "Animate a small mark beside the top heading, or briefly highlight a newly selected item.",
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
const BUTTON_HELP = {
  "Generate texture…":
    "Create a paper, linen, glass, metal, wood, flat-color or gradient image with adjustable colors, grain and edges. Generating replaces this asset; it is not an overlay on the existing image.",
  "Edit / draw":
    "Open this exact asset in the layered artwork editor. Save artwork writes its PNG and editable layers.",
  "Import image…":
    "Choose an image, then adjust its fit, crop, opacity and sampling before assigning it to this slot.",
  "Copy to slots…":
    "Copy the selected icon or component into other slots in this theme. Choose the destinations before copying.",
  Remove:
    "Remove the selected asset after confirmation. A missing slot uses Gloam's built-in fallback where available.",
  "Fill missing slots":
    "Generate starter artwork only for slots without an image. Existing assets are preserved.",
  "Generate set…":
    "Choose a starter style for the icon or component set. Existing files stay unless you explicitly enable replacement.",
  "Import atlas…":
    "Import a sprite sheet and divide it into 32×32 slots, reading left to right and then top to bottom.",
  "Export atlas":
    "Download the current slots together as one sprite-sheet PNG for editing outside Studio.",
  "Convert and assign":
    "Convert the source using these settings and save it into the selected theme slot.",
  "Extract colors from an image…":
    "Read common colors from an image and choose which theme color role receives each one.",
  "Design tab highlight…":
    "Draw the tab-selected.png nine-slice skin used when Tab highlight is set to Skin.",
  "Import tab highlight…":
    "Choose and convert artwork for the theme's tab-selected.png skin.",
  "Component settings…":
    "Open the component slots and their shared border, transparency and fill controls.",
  "Prepare assets.gfx":
    "Build Gloam's prepared asset bundle from this theme to reduce small SD-card reads. Keep the editable source assets too.",
  "Export runtime ZIP":
    "Validate and prepare the theme, then download the runtime files for installation. Editable project layers stay in the working folder.",
  "Render with local Gloam host tool":
    "Use a trusted local Gloam preview executable to check the theme with the frontend's actual renderer.",
  "Import prepared DSFONT…":
    "Import a font already converted into Gloam's DSFONT format; this does not convert a TTF or OTF file.",
  "Build saved splash into theme":
    "Convert the splash designer's saved project into this theme's splash.gsp startup animation.",
};
const CONTROL_HELP = {
  Grain: "Amount of fine texture noise. Lower values make a smoother surface.",
  Radius: "Corner rounding in pixels for the generated texture.",
  Border: "Width of the generated edge in pixels; zero removes the edge.",
  Seed: "A repeatable texture variation. The same settings and seed produce the same pattern.",
  Opacity:
    "Generated image alpha from 0 (transparent) to 255 (opaque). Reading-surface opacity is a separate per-screen percentage.",
  Surface: "The kind of texture to generate, such as paper, cloth or glass.",
};
function describeControl(node, help) {
  if (help) {
    node.title = help;
    node.setAttribute("aria-description", help);
  }
  return node;
}
function button(label, fn, primary = false) {
  return describeControl(
    el("button", {
      text: label,
      class: primary ? "primary" : "",
      onclick: () => guard(fn),
    }),
    BUTTON_HELP[label],
  );
}
for (const [id, help] of Object.entries({
  guides:
    "Show screen-safe boundaries. In Scene layout, drag the artwork box in the preview to reposition it.",
  "coverage-layer":
    "Reduce the active layer's transparency to the four coverage levels Gloam supports for translucent components.",
  "slice-grid":
    "Show the nine-slice border guides: corners remain fixed while edges and the center stretch or tile.",
  "pixel-grid":
    "Show pixel boundaries while zoomed in for precise artwork editing.",
  "resize-canvas":
    "Change the asset dimensions, optionally resampling its artwork. Runtime slots still require their documented sizes.",
  "paint-undo":
    "Undo the last artwork edit (Ctrl+Z). This is separate from saved-project undo.",
  "paint-redo": "Redo an artwork edit that was undone (Ctrl+Shift+Z).",
  "commit-art":
    "Save both the flattened runtime PNG and the project's editable layers.",
  "up-layer": "Move the selected layer above the next layer in the stack.",
  "down-layer": "Move the selected layer below the next layer in the stack.",
  "delete-layer":
    "Remove the selected artwork layer; drawing Undo can restore it.",
  validate:
    "Check paths, asset formats, size limits, layout settings, contrast and required notices before export.",
  "reload-project":
    "Read the working folder again, including external edits. Pending artwork or INI edits are handled before reloading.",
}))
  describeControl($(id), help);

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
  $("save-state").textContent = pendingCount
    ? "Working…"
    : dirtyArt
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
  if (art) await paintHistoryQueue;
  if (!(art && dirtyArt) && !(manifest && rawDraft !== null)) return;
  const choice = await editDecision(
    "Save your current edits before continuing, discard them, or keep editing.",
  );
  if (choice === "cancel") throw new CanceledEdit();
  if (choice === "save") {
    if (art && dirtyArt) await saveArtwork();
    if (manifest && rawDraft !== null) await saveManifest();
    if ((art && dirtyArt) || (manifest && rawDraft !== null)) {
      toast(
        "Newer edits are still unsaved. Finish editing before leaving this view.",
      );
      throw new CanceledEdit();
    }
  } else {
    if (art && dirtyArt) {
      dirtyArt = false;
      layers = [];
      setStage("preview", false);
    }
    if (manifest) rawDraft = null;
  }
  saveStatus();
}
async function saveManifest() {
  if (rawDraft === null) return;
  const text = rawDraft;
  await api("save", { raw: text }, false);
  if (rawDraft === text) rawDraft = null;
  saveStatus();
}
function url(endpoint, params = {}) {
  return endpoint + "?" + new URLSearchParams({ ...params, token, v: serial });
}
function assetUrl(path) {
  return url("/api/asset", { path });
}
async function api(action, data = {}, refresh = true) {
  const epoch = navigationEpoch,
    originSection = section;
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
    if (dirtyArt || rawDraft !== null)
      throw Error(
        "Newer edits arrived during save. Finish editing and try this action again.",
      );
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
      if (["workspace", "import"].includes(action)) {
        navigationHistory = [];
        navigationEpoch++;
        section = "project";
        setStage("preview", false);
        document
          .querySelectorAll("[data-section]")
          .forEach((b) =>
            b.classList.toggle("active", b.dataset.section === "project"),
          );
      }
      state = result.state;
      serial++;
      updateShell();
      if (refresh || (action === "field" && section !== originSection))
        inspect();
      renderAssets();
      refreshPreview();
    }
    saveStatus();
    return result.result;
  };
  pendingCount++;
  saveStatus();
  const current = pending.then(task);
  pending = current.catch(() => {});
  let result;
  try {
    result = await current;
  } finally {
    pendingCount--;
    saveStatus();
  }
  if (
    shouldReload &&
    epoch === navigationEpoch &&
    activeStage === "canvas" &&
    !dirtyArt
  ) {
    dirtyArt = false;
    await editAsset(reload.path, reload.width, reload.height, reload.binding);
  } else if (shouldReload) canvasNeedsReload = true;
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
    $("native-preview-back").classList.add("hidden");
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
function setStage(name, remember = true) {
  if (name !== activeStage && remember) rememberNavigation();
  if (name !== activeStage) stopMedia();
  activeStage = name;
  for (const item of ["preview", "canvas", "assets"])
    $(item + "-stage").classList.toggle("hidden", item !== name);
  document
    .querySelectorAll("[data-stage]")
    .forEach((b) => b.classList.toggle("selected", b.dataset.stage === name));
  if (name === "assets") renderAssets();
  if (name === "preview") requestAnimationFrame(() => applyPreviewZoom());
}
function selectSection(name) {
  return guard(async () => {
    if (name !== section && rawDraft !== null) await settleEdits(false, true);
    if (name !== section) {
      rememberNavigation();
      stopMedia();
    }
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
  if (target) describeControl(target, help || CONTROL_HELP[label]);
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
      value =
        current[key] ??
        (name === "layout" && key === "tabs_position"
          ? state.config.layout?.top_layout === "gallery"
            ? "top"
            : "bottom"
          : name === "layout" && key === "top_layout"
            ? "sidebar"
            : (spec.default ?? ""));
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
        if (name === "layout" && key === "top_layout") inspect();
      });
    input.onchange = () => save(input.value);
    describeControl(input, spec.help);
    input.id = "control-" + ++controlId;
    const children = [
      el("label", {
        text:
          {
            "layout.chrome": "Interface framing",
            "motion.ambient": "Header accent file",
            "motion.ambient_ticks": "Header frame interval (ticks)",
            "motion.focus": "Selection feedback",
          }[name + "." + key] || key.replaceAll("_", " "),
        htmlFor: input.id,
      }),
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
    if (name === "layout" && key === "tab_highlight") {
      const directory = state.config.components?.directory || "components";
      const path = directory + "/tab-selected.png";
      children.push(
        assetThumb(path),
        el("small", { class: "mono", text: path }),
        row(
          button("Design tab highlight…", async () => {
            await editAsset(path, 32, 32, {
              section: "components",
              key: "directory",
              value: directory,
            });
            selectedSlot = path;
            await selectSection("components");
          }),
          button("Import tab highlight…", () =>
            importImage(
              path,
              32,
              32,
              "components",
              "directory",
              null,
              directory,
            ),
          ),
          button("Component settings…", async () => {
            selectedSlot = path;
            await selectSection("components");
          }),
        ),
      );
    }
    if (name === "layout") {
      const composition = state.config.layout?.top_layout || "sidebar",
        composed = [
          "spotlight",
          "gallery",
          "journal",
          "panorama",
          "dossier",
          "portrait",
        ].includes(composition),
        side = ["sidebar", "sidebar_left"].includes(composition),
        unavailable =
          (key === "tabs_position" && !composed) ||
          (side && ["tab_visible", "tab_gap"].includes(key));
      if (unavailable) {
        input.disabled = true;
        if (key === "tab_visible") input.value = "6";
        if (key === "tab_gap") {
          input.value = "";
          input.placeholder = "Fixed";
        }
        const inheritControl = children
          .find((node) => node.classList?.contains("inherit"))
          ?.querySelector("input");
        if (inheritControl) inheritControl.disabled = !present;
        if (key === "tabs_position") {
          input.replaceChildren(
            el("option", {
              value: "",
              text: side ? "Fixed side rail" : "Fixed bottom dock",
            }),
          );
          children.push(
            note(
              "This layout fixes the tab position. Choose Spotlight, Gallery, Journal, Panorama, Dossier or Portrait for top/bottom tabs.",
            ),
          );
          if (present)
            children.push(
              button("Use layout's fixed position", () =>
                api("field", { section: "layout", key, inherit: true }),
              ),
            );
        } else
          children.push(
            el("small", {
              text: "Only horizontal docks use this setting. Side rails show up to six entries with fixed spacing.",
            }),
          );
      }
    }
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
  stopMedia();
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
  const groupNode = toolGroup("Extracted colors — choose a role");
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
    const card = group(
      label,
      assetThumb(path),
      row(
        button("Edit / draw", () =>
          editAsset(path, 256, 192, { section: "backgrounds", key }),
        ),
        button("Import image…", () =>
          importImage(path, 256, 192, "backgrounds", key),
        ),
        button("Generate texture…", () =>
          materialInspector(path, 256, 192, "backgrounds", key),
        ),
      ),
    );
    if (key.endsWith("_surface"))
      card.append(surfaceOpacityControl(key.split("_")[0], label));
    host.append(card);
  }
  renderFields(host, "backgrounds");
}
function surfaceOpacityControl(screen, label) {
  const key = screen + "_content_opacity",
    layout = state.config.layout || {},
    shared = layout.content_opacity ?? "0",
    value = layout[key] ?? shared,
    slider = el("input", {
      type: "range",
      min: 0,
      max: 100,
      step: 1,
      value,
      "aria-label": label + " opacity slider",
    }),
    percent = el("input", {
      type: "number",
      required: true,
      min: 0,
      max: 100,
      step: 1,
      value,
      "aria-label": label + " opacity percent",
    }),
    inherit = el("input", {
      type: "checkbox",
      checked: !Object.hasOwn(layout, key),
    });
  const save = (input) =>
    guard(async () => {
      if (!input.reportValidity()) return;
      slider.value = percent.value = input.value;
      inherit.checked = false;
      await api("field", { section: "layout", key, value: input.value }, false);
    });
  slider.oninput = () => (percent.value = slider.value);
  percent.oninput = () => {
    if (percent.validity.valid) slider.value = percent.value;
  };
  slider.onchange = () => save(slider);
  percent.onchange = () => save(percent);
  inherit.onchange = () =>
    guard(async () => {
      if (inherit.checked)
        slider.value = percent.value =
          state.config.layout?.content_opacity ?? "0";
      await api(
        "field",
        {
          section: "layout",
          key,
          value: percent.value,
          inherit: inherit.checked,
        },
        false,
      );
    });
  return el(
    "div",
    { class: "field" },
    el("strong", { text: "Surface opacity" }),
    el(
      "div",
      { class: "input-row" },
      slider,
      percent,
      el("span", { text: "%" }),
    ),
    el("label", {}, inherit, " Use shared opacity"),
    el("small", {
      text: "0% reveals the wallpaper; 100% keeps the surface's original opacity. Changes update the screen preview; source artwork stays intact.",
    }),
  );
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
        button("Generate texture…", () =>
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
    toolGroup(
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
    toolGroup(
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
    const image = state.assets.some((asset) => asset.path === path)
      ? await loadImage(assetUrl(path))
      : null;
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
    toolGroup(
      "Generate texture",
      note(
        "Generate a new texture for " +
          path +
          ". This replaces that output image when you generate; it does not apply an effect over the current artwork.",
      ),
      field("Surface", style),
      field("Base color", color),
      field("Edge color", edge),
      ...fields.map((f) => f[1]),
      button(
        "Generate " + width + "×" + height,
        async () => {
          const epoch = navigationEpoch;
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
          if (epoch !== navigationEpoch) {
            log("Artwork saved; current view kept.");
            return;
          }
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
    toolGroup(
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
          const epoch = navigationEpoch;
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
          if (epoch !== navigationEpoch) {
            log("Artwork saved; current view kept.");
            return;
          }
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
function motionDemo(kind) {
  const image = el("img", {
      src: url("/api/motion-preview", { kind, play: "0" }),
      alt:
        kind === "ambient"
          ? "Actual header accent position and enlarged frame detail"
          : "Selected-row edge gleam demonstration",
      class: "texture-preview",
      "data-motion-demo": kind,
    }),
    status = el("small", {
      role: "status",
      text: "Stopped. Press Play to demonstrate the effect.",
    });
  let playing = false;
  image.stopMotion = () => {
    if (!playing) return;
    playing = false;
    image.src = url("/api/motion-preview", { kind, play: "0" });
    status.textContent = "Stopped; the project is still open.";
  };
  image.onerror = () => {
    playing = false;
    status.textContent =
      "Preview unavailable. Check or reimport the accent file, then try again.";
  };
  return el(
    "div",
    {},
    image,
    row(
      button(
        "Play " + (kind === "ambient" ? "header accent" : "selection feedback"),
        () => {
          playing = true;
          image.src = url("/api/motion-preview", { kind, play: "1" });
          status.textContent =
            kind === "focus" && state.config.motion?.focus !== "pulse"
              ? "Feedback is Off. Select pulse below, then press Play."
              : "Playing a looping demonstration. Stop or leave this view to end it.";
        },
      ),
      button(
        "Stop " + (kind === "ambient" ? "header accent" : "selection feedback"),
        () => image.stopMotion(),
      ),
    ),
    status,
  );
}
function motionInspector(host) {
  host.append(
    note(
      "These are two small browsing effects. They do not animate the wallpaper or startup splash; use Startup splash for a full-screen intro.",
    ),
  );
  const header = group(
    "1. Top-screen header accent",
    note(
      "Your imported image appears as a 16×16 mark beside the header title, immediately left of the battery icon. The preview outlines its reserved position and shows a larger detail underneath.",
    ),
  );
  const asset = state.assets.find(
    (a) => a.path === state.config.motion?.ambient,
  );
  if (asset) {
    const frames = Math.max(0, Math.min(8, (asset.bytes - 16) / 2304));
    header.append(
      el("p", {
        text:
          frames +
          " prepared frame(s). A single frame is a still image, not an animation.",
      }),
      motionDemo("ambient"),
    );
  } else
    header.append(
      note(
        "No header accent imported yet. Import a small GIF for animation, or a PNG for a still mark.",
      ),
    );
  const [cf, count] = number("Maximum frames to keep", 8, 1, 8);
  header.append(
    cf,
    button(
      "Import header GIF / PNG…",
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
  renderFields(header, "motion", ["ambient", "ambient_ticks"]);
  header.append(
    note(
      "GIF frames are sampled evenly, up to the limit above, and resized to 32×32 for storage. Gloam displays them at 16×16. Frame interval sets uniform playback timing; original GIF delays are not retained. On the console, the accent advances while the browser is idle; Reduced motion holds the first frame.",
    ),
  );
  const focus = group(
    "2. Selection edge feedback",
    note(
      "A short gleam along the left edge of the item you just selected, lasting about 0.2 seconds. The title icon and wallpaper stay still. This demonstration repeats a selection so the brief effect is easy to see; contrast depends on your selection skin.",
    ),
    motionDemo("focus"),
  );
  renderFields(focus, "motion", ["focus"]);
  focus.append(
    note(
      "Reduced motion disables this gleam. It does not replace animated DS/DSi banner icons, which keep their own title animation.",
    ),
  );
  host.append(header, focus);
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
        const previous = captureNavigation(),
          epoch = navigationEpoch;
        const file = await api("native", {
          executable: native.input.value,
          sample: $("sample").value,
        });
        if (epoch !== navigationEpoch) {
          log("Native preview saved in exports; current view kept.");
          return;
        }
        rememberNavigation(previous);
        clearTimeout(previewTimer);
        $("native-preview-back").classList.remove("hidden");
        document.querySelector(".caption").textContent =
          "Native Gloam renderer · synthetic library";
        $("preview").src = url("/api/export-file", { path: file });
        setStage("preview", false);
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
  if (paintHistoryBusy) return false;
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
  return true;
}
async function decodePaintDocument(s) {
  const restored = [];
  for (const layer of s.layers) {
    const c = canvas(s.width, s.height);
    c.getContext("2d").drawImage(await loadImage(layer.data), 0, 0);
    restored.push({ ...layer, canvas: c });
  }
  return { layers: restored, width: s.width, height: s.height, index: s.index };
}
function applyPaintDocument(s) {
  artWidth = s.width;
  artHeight = s.height;
  layers = s.layers;
  layerIndex = Math.max(0, Math.min(layers.length - 1, s.index));
  dirtyArt = true;
  paintRender();
}
async function restorePaint(s) {
  applyPaintDocument(await decodePaintDocument(s));
}
function stepPaintHistory(redo = false) {
  const task = async () => {
    const source = redo ? paintFuture : paintHistory,
      destination = redo ? paintHistory : paintFuture;
    if (!source.length) return;
    paintHistoryBusy = true;
    drawing = null;
    paintRender();
    try {
      const current = snapshotPaint(),
        restored = await decodePaintDocument(source.at(-1));
      source.pop();
      destination.push(current);
      applyPaintDocument(restored);
    } finally {
      paintHistoryBusy = false;
      paintRender();
    }
  };
  const operation = paintHistoryQueue.then(task);
  paintHistoryQueue = operation.catch(() => {});
  return operation;
}

async function editAsset(path, width = 32, height = 32, binding = null) {
  const previous = captureNavigation();
  await settleEdits(true, false);
  const epoch = navigationEpoch;
  const doc = await api("artboard-load", { path }, false);
  let image = null;
  if (!doc && state.assets.some((a) => a.path === path))
    image = await loadImage(assetUrl(path));
  const restored = doc ? await decodePaintDocument(doc) : null;
  if (!navigationRestoring && epoch !== navigationEpoch)
    throw new CanceledEdit();
  if (dirtyArt) {
    toast(
      "Newer artwork edits kept; select the other asset again when finished.",
    );
    throw new CanceledEdit();
  }
  activeAsset = path;
  canvasNeedsReload = false;
  loadedAsset = path;
  assetBinding = binding;
  artWidth = width;
  artHeight = height;
  if (restored) {
    applyPaintDocument(restored);
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
  if (previous.stage !== "canvas" || previous.asset !== path)
    rememberNavigation(previous);
  setStage("canvas", false);
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
  document.querySelector(".artboard-scroll").inert = paintHistoryBusy;
  $("layer-list").inert = paintHistoryBusy;
  $("asset-assignment").disabled = paintHistoryBusy;
  $("paint-undo").disabled = !paintHistory.length;
  $("paint-redo").disabled = !paintFuture.length;
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
          if (!checkpointPaint()) return;
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
          if (!checkpointPaint()) return;
          l.opacity = Number(e.target.value) / 100;
          paintRender();
        },
      }),
      blend = select(["source-over", "multiply", "screen", "overlay"], l.blend);
    blend.onchange = () => {
      if (!checkpointPaint()) return;
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
    if (!checkpointPaint()) return;
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
$("paint-undo").onclick = () => guard(() => stepPaintHistory());
$("paint-redo").onclick = () => guard(() => stepPaintHistory(true));
async function saveArtwork() {
  await paintHistoryQueue;
  if (!layers.length) return;
  if (
    activeAsset !== loadedAsset &&
    state.assets.some((a) => a.path === activeAsset) &&
    !confirm("Replace existing artwork at " + activeAsset + "?")
  )
    throw new CanceledEdit();
  const path = activeAsset,
    binding = assetBinding ? { ...assetBinding } : null,
    drawingDocument = snapshotPaint(),
    savedDrawing = JSON.stringify(drawingDocument);
  await api("artboard-save", {
    path,
    binding,
    data: composite().toDataURL("image/png"),
    document: drawingDocument,
  });
  if (activeAsset !== path) {
    toast("Saved " + path + "; current artwork kept.");
    return;
  }
  loadedAsset = path;
  dirtyArt =
    JSON.stringify(snapshotPaint()) !== savedDrawing ||
    JSON.stringify(assetBinding) !== JSON.stringify(binding);
  paintRender();
  toast(
    dirtyArt
      ? "Earlier artwork saved; newer edits are still unsaved."
      : "Artwork and editable layers saved",
  );
}
$("commit-art").onclick = () => guard(saveArtwork);
$("add-layer").onclick = () =>
  guard(() => {
    if (layers.length >= 16) throw Error("Use at most 16 layers per artboard.");
    if (!checkpointPaint()) return;
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
  const epoch = navigationEpoch,
    asset = activeAsset;
  if (layers.length >= 16) throw Error("Use at most 16 layers.");
  const file = droppedFile || (await upload("image/*"));
  if (!file) return;
  const image = await loadImage(await fileData(file));
  await paintHistoryQueue;
  if (
    epoch !== navigationEpoch ||
    asset !== activeAsset ||
    activeStage !== "canvas"
  ) {
    toast("Layer import canceled; current view kept.");
    return;
  }
  if (layers.length >= 16) throw Error("Use at most 16 layers.");
  if (!checkpointPaint()) return;
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
    if (!checkpointPaint()) return;
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
  if (!checkpointPaint()) return;
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
    if (!checkpointPaint()) return;
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
  if (!checkpointPaint()) return;
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
  if (!checkpointPaint()) return;
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
  if (!checkpointPaint()) return;
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
  toast(
    dirtyArt || rawDraft !== null
      ? "Completed saves kept; newer edits are still unsaved."
      : "Project saved in " + state.workspace,
  );
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
const PREVIEW_ZOOM_STEPS = [0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4, 6, 8];
function applyPreviewZoom(reset = false) {
  const viewport = $("preview-viewport");
  if (!viewport.clientWidth || !viewport.clientHeight) return;
  const image = $("preview"),
    previous = image.getBoundingClientRect(),
    bounds = viewport.getBoundingClientRect(),
    centerX = bounds.left + viewport.clientWidth / 2,
    centerY = bounds.top + viewport.clientHeight / 2,
    pointX = previous.width ? (centerX - previous.left) / previous.width : 0.5,
    pointY = previous.height ? (centerY - previous.top) / previous.height : 0.5;
  previewScale =
    $("zoom").value === "fit"
      ? Math.max(
          0.25,
          Math.min(
            3,
            (viewport.clientWidth - 70) / 256,
            (viewport.clientHeight - 70) / 396,
          ),
        )
      : Number($("zoom").value);
  const width = Math.round(256 * previewScale),
    height = Math.round(396 * previewScale);
  image.width = width;
  image.height = height;
  image.style.width = width + "px";
  image.style.height = height + "px";
  if (reset) {
    viewport.scrollLeft = (viewport.scrollWidth - viewport.clientWidth) / 2;
    viewport.scrollTop = (viewport.scrollHeight - viewport.clientHeight) / 2;
  } else {
    const next = image.getBoundingClientRect();
    viewport.scrollLeft += next.left + pointX * next.width - centerX;
    viewport.scrollTop += next.top + pointY * next.height - centerY;
  }
  $("zoom-level").textContent = Math.round(previewScale * 100) + "%";
  $("zoom-out").disabled = previewScale <= PREVIEW_ZOOM_STEPS[0];
  $("zoom-in").disabled = previewScale >= PREVIEW_ZOOM_STEPS.at(-1);
}
function stepPreviewZoom(direction) {
  const next =
    direction > 0
      ? PREVIEW_ZOOM_STEPS.find((v) => v > previewScale + 0.001)
      : [...PREVIEW_ZOOM_STEPS].reverse().find((v) => v < previewScale - 0.001);
  if (next === undefined) return;
  $("zoom").value = String(next);
  applyPreviewZoom();
}
$("zoom").onchange = () => applyPreviewZoom($("zoom").value === "fit");
$("zoom-in").onclick = () => stepPreviewZoom(1);
$("zoom-out").onclick = () => stepPreviewZoom(-1);
$("zoom-fit").onclick = () => {
  $("zoom").value = "fit";
  applyPreviewZoom(true);
};
const previewViewport = $("preview-viewport");
let panDrag = null;
previewViewport.onpointerdown = (e) => {
  if (e.defaultPrevented || panDrag || ![0, 1].includes(e.button)) return;
  e.preventDefault();
  previewViewport.focus({ preventScroll: true });
  panDrag = {
    pointer: e.pointerId,
    x: e.clientX,
    y: e.clientY,
    left: previewViewport.scrollLeft,
    top: previewViewport.scrollTop,
  };
  previewViewport.setPointerCapture(e.pointerId);
  previewViewport.classList.add("panning");
};
previewViewport.onpointermove = (e) => {
  if (!panDrag || panDrag.pointer !== e.pointerId) return;
  previewViewport.scrollLeft = panDrag.left + panDrag.x - e.clientX;
  previewViewport.scrollTop = panDrag.top + panDrag.y - e.clientY;
};
function endPreviewPan(e) {
  if (!panDrag || e.pointerId !== panDrag.pointer) return;
  panDrag = null;
  previewViewport.classList.remove("panning");
  if (previewViewport.hasPointerCapture(e.pointerId))
    previewViewport.releasePointerCapture(e.pointerId);
}
previewViewport.onpointerup =
  previewViewport.onpointercancel =
  previewViewport.onlostpointercapture =
    endPreviewPan;
previewViewport.onkeydown = (e) => {
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  if (["+", "=", "-", "_", "0"].includes(e.key)) {
    e.preventDefault();
    if (e.key === "0") $("zoom-fit").click();
    else stepPreviewZoom(["+", "="].includes(e.key) ? 1 : -1);
  }
};
for (const id of ["sample", "preview-view", "selected", "guides"])
  $(id).onchange = refreshPreview;
document.querySelectorAll("[data-stage]").forEach(
  (b) =>
    (b.onclick = () =>
      guard(async () => {
        if (activeStage === "canvas" && b.dataset.stage !== "canvas")
          await settleEdits(true, false);
        if (b.dataset.stage === "canvas" && canvasNeedsReload) {
          await editAsset(activeAsset, artWidth, artHeight, assetBinding);
          return;
        }
        setStage(b.dataset.stage);
      })),
);
$("view-back").onclick = $("native-preview-back").onclick = () => guard(goBack);
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
  if (dirtyArt || rawDraft !== null || pendingCount) {
    e.preventDefault();
    e.returnValue = "";
  }
});
window.addEventListener("keydown", (e) => {
  if (e.defaultPrevented || e.isComposing) return;
  if (e.key === "Escape" || (e.altKey && e.key === "ArrowLeft")) {
    if (document.querySelector("dialog[open]")) return;
    e.preventDefault();
    guard(goBack);
    return;
  }
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
      guard(() => stepPaintHistory(e.shiftKey));
    } else guard(() => api(e.shiftKey ? "redo" : "undo"));
  }
});
let coverDrag = null;
$("preview").onpointerdown = (e) => {
  if (
    e.button !== 0 ||
    e.altKey ||
    section !== "layout" ||
    !$("guides").checked ||
    state.config.layout?.top_layout !== "scene"
  )
    return;
  const rect = e.target.getBoundingClientRect(),
    x = ((e.clientX - rect.left) * 256) / rect.width,
    y = ((e.clientY - rect.top) * 396) / rect.height;
  const layout = state.config.layout,
    ox = Number(layout.scene_cover_x || 18),
    oy = Number(layout.scene_cover_y || 34),
    width = Number(layout.scene_cover_width || 48),
    height = Number(layout.scene_cover_height || 72);
  if (
    x >= ox - 2 &&
    x <= ox + width + 2 &&
    y >= oy - 2 &&
    y <= oy + height + 2
  ) {
    e.preventDefault();
    e.stopPropagation();
    coverDrag = {
      x,
      y,
      ox: Number(state.config.layout.scene_cover_x || 18),
      oy: Number(state.config.layout.scene_cover_y || 34),
    };
    e.target.setPointerCapture(e.pointerId);
  }
};
$("preview").onpointercancel = () => {
  coverDrag = null;
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
