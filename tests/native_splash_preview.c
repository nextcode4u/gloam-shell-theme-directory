/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Independent bridge for byte-for-byte PC/native motion preview comparisons. */
#include "splash.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
static struct {
    unsigned before;
    uint16_t pixels[256 * 192];
    unsigned after;
} top, bottom;
int main(int argc, char **argv)
{
    assert(argc == 5);
    Splash splash = {0};
    assert(splash_load(&splash, argv[1]));
    top.before = top.after = bottom.before = bottom.after = 0xC0FFEE;
    splash_render(&splash, strtoul(argv[2], NULL, 10), atoi(argv[3]) != 0, top.pixels,
                  bottom.pixels);
    assert(top.before == 0xC0FFEE && top.after == 0xC0FFEE);
    assert(bottom.before == 0xC0FFEE && bottom.after == 0xC0FFEE);
    FILE *out = fopen(argv[4], "wb");
    assert(out);
    for (int screen = 0; screen < 2; screen++)
        for (int i = 0; i < 256 * 192; i++) {
            unsigned color = (screen ? bottom.pixels : top.pixels)[i];
            for (int shift = 0; shift < 15; shift += 5)
                assert(fputc(((color >> shift) & 31) * 255 / 31, out) != EOF);
        }
    assert(!fclose(out));
    splash_close(&splash);
}
