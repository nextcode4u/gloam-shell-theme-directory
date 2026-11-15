/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Run against Gloam's host-check objects: load real theme assets, exercise bounds,
 * and capture actual renderer output. No console or SD card is touched. */
#include "app.h"
#include "audio.h"
#include "browser.h"
#include "font_pack.h"
#include "picker.h"
#include "renderer.h"
#include "settings.h"
#include "theme_motion.h"
#include "themes.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static App app;
static struct {
    unsigned pre;
    uint16_t data[256 * 192];
    unsigned post;
} top, bottom;
static void draw(void)
{
    top.pre = bottom.pre = 0x12345678;
    top.post = bottom.post = 0x87654321;
    render_app(&app, top.data, bottom.data, "10:24");
    assert(top.pre == 0x12345678 && bottom.pre == 0x12345678);
    assert(top.post == 0x87654321 && bottom.post == 0x87654321);
}
static void ppm(const char *dir, const char *theme, const char *kind, uint16_t *pixels)
{
    char path[1024];
    snprintf(path, sizeof path, "%s/%s-%s.ppm", dir, theme, kind);
    FILE *f = fopen(path, "wb");
    assert(f);
    fprintf(f, "P6\n256 192\n255\n");
    for (int i = 0; i < 256 * 192; i++) {
        unsigned p = pixels[i];
        unsigned char rgb[] = {(p & 31) * 255 / 31, ((p >> 5) & 31) * 255 / 31,
                               ((p >> 10) & 31) * 255 / 31};
        assert(fwrite(rgb, 1, 3, f) == 3);
    }
    assert(!fclose(f));
}
int main(int argc, char **argv)
{
    assert(argc == 4);
    app_init(&app, argv[1], true, true);
    themes_open(&app);
    int selected = 0;
    while (selected < app.themes.count && strcmp(app.themes.ids[selected], argv[2]))
        selected++;
    assert(selected < app.themes.count);
    themes_move(&app, selected - app.themes.selected);
    themes_preview(&app);
    if (!app.themes.ready) {
        fprintf(stderr, "Rejected %s: %s\n", argv[2], app.themes.status);
        return 1;
    }
    draw();
    themes_cancel(&app);
    themes_open(&app);
    themes_move(&app, selected - app.themes.selected);
    themes_preview(&app);
    assert(app.themes.ready);
    themes_apply(&app);
    assert(!strcmp(app.theme_id, argv[2]));
    for (int i = 0; i < THEME_ICON_COUNT; i++)
        assert(themes_icon(&app.themes.active, i));
    for (int i = 0; i < THEME_COMPONENT_COUNT; i++)
        assert(themes_component(&app.themes.active, i));
    assert(app.themes.active.format_version == 2);
    assert(app.themes.active.component_coverage && app.themes.active.custom_heading);
    unsigned soft = 0;
    for (int g = 0; g < app.themes.active.font.glyph_count; g++)
        for (int y = 0; y < app.themes.active.font.height; y++)
            for (int x = 0; x < app.themes.active.font.advance[g]; x++) {
                unsigned v = (app.themes.active.font.rows[g][y] >> (2 * x)) & 3;
                soft += v == 1 || v == 2;
            }
    assert(soft);
    const uint8_t *coverage = themes_component_alpha(&app.themes.active, THEME_CARD);
    assert(coverage);
    unsigned translucent = 0;
    for (unsigned pixel = 0; pixel < 1024; pixel++) {
        unsigned alpha = (coverage[pixel / 4] >> ((pixel % 4) * 2)) & 3;
        translucent += alpha == 1 || alpha == 2;
    }
    assert(translucent);
    app.audio.mode = 1;
    audio_reload(&app);
    assert((app.audio.music.samples != NULL) == (*app.themes.active.music != 0));
    for (int i = 0; i < 3; i++)
        assert((app.audio.effects[i].samples != NULL) == (*app.themes.active.sounds[i] != 0));
    app_category(&app, CATEGORY_GAMES);
    for (int f = 0; f < 180; f++)
        app_tick(&app);
    const uint8_t *ambient_alpha;
    assert(themes_motion_frame(&app, &ambient_alpha));
    /* Prepared sprites must preserve exactly what the editable PNGs render. */
    static uint16_t prepared_top[256 * 192], prepared_bottom[256 * 192];
    draw();
    memcpy(prepared_top, top.data, sizeof prepared_top);
    memcpy(prepared_bottom, bottom.data, sizeof prepared_bottom);
    char prepared_path[PATH_CAP];
    snprintf(prepared_path, sizeof prepared_path, "%s", app.themes.active.prepared_assets);
    app.themes.active.prepared_assets[0] = 0;
    themes_icons_load(&app.themes.active, false);
    themes_components_load(&app.themes.active, false);
    draw();
    assert(!memcmp(prepared_top, top.data, sizeof prepared_top));
    assert(!memcmp(prepared_bottom, bottom.data, sizeof prepared_bottom));
    snprintf(app.themes.active.prepared_assets, PATH_CAP, "%s", prepared_path);
    /* Present synthetic paths as SD paths, without exposing the host workspace. */
    char saved_path[PATH_CAP];
    snprintf(saved_path, sizeof saved_path, "%s", app.locations[app.category].path);
    snprintf(app.locations[app.category].path, PATH_CAP, "sd:/roms");
    draw();
    ppm(argv[3], argv[2], "top", top.data);
    ppm(argv[3], argv[2], "bottom", bottom.data);
    snprintf(app.locations[app.category].path, PATH_CAP, "%s", saved_path);
    app_category(&app, CATEGORY_HOME);
    app.locations[CATEGORY_HOME].selected = 1;
    draw();
    ppm(argv[3], argv[2], "home-top", top.data);
    ppm(argv[3], argv[2], "home-bottom", bottom.data);
    for (int view = 0; view < BROWSER_STYLE_COUNT; view++)
        for (int size = 0; size < 2; size++) {
            app.browser_style = view;
            app.icon_size = size;
            browser_reflow(&app);
            for (int category = 0; category <= CATEGORY_SYSTEM; category++) {
                app_category(&app, category);
                draw();
                app.detail_tab = 1;
                draw();
                app.detail_tab = 0;
                app.reduced_motion = true;
                draw();
                app.reduced_motion = false;
            }
        }
    app.advanced_settings = true;
    settings_open(&app);
    draw();
    ppm(argv[3], argv[2], "settings", bottom.data);
    app.settings.open = false;
    assert(picker_open_background(&app, 1));
    for (int frame = 0; frame < 60; frame++)
        picker_tick(&app);
    assert(app.picker.count > 0 && !app.picker.failed);
    snprintf(app.picker.path, PATH_CAP, "sd:/media");
    draw();
    ppm(argv[3], argv[2], "picker-top", top.data);
    ppm(argv[3], argv[2], "picker-bottom", bottom.data);
    picker_close(&app);
    themes_motion_reset();
    audio_free_clip(&app.audio.music);
    for (int i = 0; i < 3; i++)
        audio_free_clip(&app.audio.effects[i]);
    printf("PASS %s: load, cancel/apply, prepared/PNG parity, icon/component banks, coverage font, "
           "music/cues, all "
           "views/sizes/categories and settings bounds\n",
           argv[2]);
    return 0;
}
