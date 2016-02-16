
#include <assert.h>
#include <stdio.h>
#include <stdbool.h>
#include "libpuz/puz.h"

typedef unsigned char u8;

bool flWithSolution = true;

#define PRINTF(args...) fprintf(fp, ##args)

int main(int argc, const char *argv[])
{
    char buf[8192];
    FILE *fp = fopen(argv[1], "r");
    if (fp == NULL) {
        perror(argv[1]);
        return -1;
    }
    int r = fread(buf, 1, sizeof(buf), fp);
    fclose(fp);

    if (buf[0x2C] == 0) { 
        buf[0x2C] = 15;
    }
    if (buf[0x2D] == 0) { 
        buf[0x2D] = 15;
    }
    if (buf[0x2E] == 0) { 
        buf[0x2E] = 15;
    }

    struct puzzle_t puz;
    struct puzzle_t *p = puz_load(&puz, PUZ_FILE_UNKNOWN, buf, r); 

    int w = puz_width_get(p);
    int h = puz_height_get(p);
    u8 *sol = puz_solution_get(p);
    u8 *grid = puz_grid_get(p);
    u8 *title = puz_title_get(p);
    u8 *author = puz_author_get(p);
    u8 *copyright = puz_copyright_get(p);
    u8 *notes = puz_notes_get(p);
    u8 *rebus = puz_has_rebus(p) ? puz_rebus_get(p) : NULL;
    u8 *extras = puz_has_extras(p) ? puz_extras_get(p) : NULL;

    if (!title) {
        fprintf(stderr, "error on '%s'\n", argv[1]);
        exit(0);
    }

    fp = fopen(argv[2], "w");
    if (fp == NULL) {
        perror(argv[2]);
        fp = stderr;
    }

    PRINTF("Title: %s\n", title);
    PRINTF("Author: %s\n", author);
    PRINTF("Copyright: %s\n", copyright);
    if (rebus) PRINTF("Rebus: %s\n", rebus);
    if (extras) PRINTF("Extras: %s\n", extras);
    if (notes) PRINTF("Notes: %s\n", notes);
//     PRINTF("puz_rtblstr_get: %s\n", puz_rtblstr_get(p));

    assert(!puz_has_rusr(p));

    if (rebus) {
        int i;
        for (i=0; i < puz_rebus_count_get(p); ++i) {
            PRINTF("rtbl %d: %s\n", i, puz_rtbl_get(p, i));
        }
    }

    int c, j;
    int i=0;
    for (i=0,r=0; r < h; ++r) {
       PRINTF("\n ");
       for (c=0; c < w; ++c) {
           PRINTF("%c", sol[i++]);
       }
    }

    PRINTF("\n");

    int nclues = puz_clue_count_get(p);
    int cluenum = 1;
    int n = 0;
    i = 0;

    int nAcross = 0;
    int nDown = 0;
    char across[256][128];
    char down[256][128];
#define CELL(R, C) (sol[(R)*w+(C)])
#define ISBLK(R, C) ((C) < 0 || (R) < 0 || (C) >= w || (R) >= h || CELL(R, C) == '.')

    for (r=0; r < h; ++r) {
       for (c=0; c < w; ++c) {
           bool newclue = false;
           switch (grid[i++]) {
            case '-':
                if (ISBLK(r, c-1)) {
                    char answer[128] = { 0 };
                    for (j=0; !ISBLK(r, j+c); ++j) answer[j] = CELL(r, j+c);
                    if (j > 1) {
                        u8 *clue = puz_clue_get(p, n++);
                        if (flWithSolution) {
                            snprintf(across[nAcross++], 128, "A%d. %s ~ %s", cluenum, clue, answer);
                        } else {
                            snprintf(across[nAcross++], 128, "A%d. %s", cluenum, clue);
                        }
                        newclue = true;
                    }
                }
                if (ISBLK(r-1, c)) {
                    char answer[128] = { 0 };
                    for (j=0; !ISBLK(j+r, c); ++j) answer[j] = CELL(j+r, c);
                    if (j > 1) {
                        u8 *clue = puz_clue_get(p, n++);
                        if (flWithSolution) {
                            snprintf(down[nDown++], 128, "D%d. %s ~ %s", cluenum, clue, answer);
                        } else {
                            snprintf(down[nDown++], 128, "D%d. %s", cluenum, clue);
                        }
                        newclue = true;
                    }
                }
                if (newclue) {
                    cluenum++;
                }
                break;
            case '.':
            default:
                break;
           };
       }
    }

    if (nclues != nAcross + nDown) {
        printf("#Across=%d, #Down=%d, #Clues=%d\n", nAcross, nDown, nclues);
        assert(nclues == nAcross + nDown);
    }

    PRINTF("\n");
    for (i=0; i < nAcross; ++i) { PRINTF("%s\n", across[i]); }
    PRINTF("\n");
    for (i=0; i < nDown; ++i) { PRINTF("%s\n", down[i]); }
    PRINTF("\n");
    if (notes && notes[0]) {
        PRINTF("---\n%s\n", notes);
    }

    if (false && flWithSolution) {
        for (i=0,r=0; r < h; ++r) {
            PRINTF("\n ");
            for (c=0; c < w; ++c) {
                PRINTF("%c", sol[i++]);
            }
        }
    }
    PRINTF("\n ");

    fclose(fp);

    return 0;
}
