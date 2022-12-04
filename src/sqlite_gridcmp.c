#include <sqlite3ext.h>
SQLITE_EXTENSION_INIT1

#include <stddef.h>

void
sql_gridcmp(sqlite3_context *ctx, int argc, sqlite3_value **argv)
{
    // assert(argc == 2)
    int grid1_size = sqlite3_value_bytes(argv[0]);
    int grid2_size = sqlite3_value_bytes(argv[1]);

    int rowlen = 0;
    if (grid1_size == 239) {
        rowlen = 16;
    }

    if (grid1_size != grid2_size) {
        sqlite3_result_null(ctx);
        return;
    }

    const unsigned char *grid1 = sqlite3_value_text(argv[0]);
    const unsigned char *grid2 = sqlite3_value_text(argv[1]);

    int nmatches = 0;
    int nblocks = 0;
    int ntotal = 0;
    for (int i=0; i < grid1_size; ++i) {
        if (grid1[i] == '|') {
            continue;
        }
        ntotal++;

        if (grid1[i] == grid2[i]) {
            if (grid1[i] == '#') nblocks++;
            nmatches++;
        }
    }

    int t_nmatches = 0;
    if (rowlen) {
        // compare transposed
        for (int i=0; i < grid2_size; ++i) {
            int y = i/rowlen;
            int x = i%rowlen;

            if (grid1[i] == grid2[x*rowlen+y]) {
                t_nmatches++;
            }
        }
    }

    if (ntotal == nblocks) {
        sqlite3_result_null(ctx);
        return;

    }

    int pct = (nmatches - nblocks)*100/(ntotal - nblocks);
    int t_pct = (t_nmatches - nblocks)*100/(ntotal - nblocks);
    if (t_pct > pct) {
        sqlite3_result_int(ctx, -t_pct);
    } else {
        sqlite3_result_int(ctx, pct);
    }
}

int
sqlite3_gridcmp_init(sqlite3 *db, char **pzErrMsg, const sqlite3_api_routines *pApi)
{
    SQLITE_EXTENSION_INIT2(pApi);
    return sqlite3_create_function(db, "gridcmp", 2,
            SQLITE_UTF8 | SQLITE_DETERMINISTIC | SQLITE_INNOCUOUS,
            NULL, sql_gridcmp, NULL, NULL);
}
