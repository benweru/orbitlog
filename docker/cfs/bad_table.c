#include "cfe_tbl_filedef.h"
#include "sample_app_tbl.h"

/* Int1 is past SAMPLE_APP_PLATFORM_TBL_ELEMENT_1_MAX (10). */
SAMPLE_APP_ExampleTable_t ExampleTable = {11, 2};

CFE_TBL_FILEDEF(ExampleTable, SAMPLE_APP.ExampleTable, Bad Int1 table, b11.tbl)
