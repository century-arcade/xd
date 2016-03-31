#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <dirent.h>
#include <sys/stat.h>
#include <string.h>

typedef void (*FileFunc_t)(const char *pathname);

void walk_dir(const char *basedir, FileFunc_t func)
{
    DIR *dir = opendir(basedir);
    
    if(dir == NULL)
    {
        perror("opendir()");
        return;
    }

    struct dirent *ent;

    while((ent = readdir(dir)) != NULL)
    {
        // do not allow "." or ".."
        if(strcmp(ent->d_name, ".") == 0 || strcmp(ent->d_name, "..") == 0)
        {
            continue;
        }
        
        char entpath[512] = "";
        strcat(entpath, basedir);
        strcat(entpath, "/");
        strcat(entpath, ent->d_name);

        struct stat s;
        if (stat(entpath, &s) < 0) {
            perror(entpath);
        }

        if (S_ISDIR(s.st_mode))
        {
            walk_dir(entpath, func);
        }
        else // file
        {
            (*func)(entpath);
        }
    }
    
    closedir(dir);
}

typedef struct Grid_t {
    char filename[128];
    char grid[32*32];
    int  gridsize;
    int  nrows;
    int  ncols;
} Grid_t;

Grid_t grids[100000];
int g_ngrids = 0;

void transpose_grid(Grid_t *out, const Grid_t *g)
{
    int row = 0;
    int col = 0;
    int ncols = 0;
    for (int i=0; i < g->gridsize; ++i) {
        char c = g->grid[i];
        if (c == '\n') {
            row++;
            ncols = col;
            col = 0;
            continue;
        }
        out->grid[col*(g->nrows+1) + row] = c;
        col++;
    }
    for (int i=0; i < row; ++i) {
        out->grid[i*(g->nrows+1) + g->nrows+1] = '\n';
    }
    out->ncols = row;
    out->nrows = ncols+1;
    out->gridsize = out->ncols * out->nrows;
    strcpy(out->filename, g->filename);
    strcat(out->filename, ".transposed");
//    out->grid[g->nrows * ncols] = 0;
}

void import_grid(const char *fn)
{
    FILE *fp = fopen(fn, "r");
    if (fp == NULL) {
        perror(fn);
        exit(1);
        return;
    }

    char buf[10240];
    size_t n = fread(buf, 1, sizeof(buf), fp);
    int gridstart = 0;
    int gridend = 0;
    int nrows = 0;
    for (int i=0; i < n; i++) {
        if (buf[i] == '\n') {
            if (buf[i+1] == '\n' && buf[i+2] == '\n') {
                if (gridstart == 0) {
                    nrows = 0;
                    gridstart = i+3;
                    i += 3;
                } else {
                    gridend = i;
                    break;
                }
            } else {
                nrows++;
            }
        }
    }

    fclose(fp);

    if (gridend == 0) {
        return;
    }
    int gridsize = gridend - gridstart;
    if (gridsize == 0) {
        return;
    }

    assert(gridsize >= 0);

    Grid_t *g = &grids[g_ngrids++];
    strcpy(g->filename, fn);
    memcpy(g->grid, &buf[gridstart], gridsize);
    g->grid[gridsize] = 0;
    g->gridsize = gridsize;
    g->nrows = nrows;

// #ifdef TEST
    Grid_t tg = { 0 };
    transpose_grid(&tg, g);
    Grid_t untg = { 0 };
    transpose_grid(&untg, &tg);
    assert(strcmp(untg.grid, g->grid) == 0);
//#endif
}

void cmp_grids(const Grid_t *g1, const Grid_t *g2, int *out_nmatching, int *out_nblocks)
{
    int nmatches = 0;
    int nblocks = 0;
    for (int i=0; i < g2->gridsize; ++i) {
        if (g1->grid[i] == g2->grid[i]) {
            nmatches++;
            if (g1->grid[i] == '#') {
                nblocks++;
            }
        }
    }
    *out_nmatching = nmatches;
    *out_nblocks = nblocks;
}

int print_matches(const Grid_t *needle, const Grid_t *g2) 
{
    if (needle->gridsize != g2->gridsize) return 0;

    int nmatch = 0;
    int nblock = 0;
    cmp_grids(needle, g2, &nmatch, &nblock);
    int pct = (nmatch - nblock)*100/(g2->gridsize - nblock);
    if (pct >= 40) {
        printf("%d  %s  %s\n", pct, needle->filename, g2->filename);
    }
    return pct;
}

int main(int argc, char *argv[])
{
    walk_dir("crosswords", import_grid);
    fprintf(stderr, "%d grids\n", g_ngrids);

    for (int i=0; i < g_ngrids; ++i) {
        if (i % 100 == 0) {
            fprintf(stderr, "%d\n", i);
        }

        const Grid_t *g1 = &grids[i];
        for (int j=0; j < g_ngrids; ++j) {
            if (i == j) continue;
            print_matches(g1, &grids[j]);
        }

        Grid_t tg = { 0 };
        transpose_grid(&tg, g1);
        for (int j=0; j < g_ngrids; ++j) {
            if (i == j) continue;
            print_matches(&tg, &grids[j]);
        }
    }
    return 0;
}

