/*
 * Tiny app used by the cfs_app_crash_restart injector.
 * FAULT_APP_EXIT_CC makes the app call CFE_ES_ExitApp(APP_ERROR), which is
 * the error-exit path (CFE_ES_ERREXIT_APP_*_EID). A later CFE_ES_RESTART_APP
 * is sent only while the app is still registered; see the injector.
 */
#include "cfe.h"
#include "cfe_msg.h"

#define FAULT_APP_CMD_MID 0x18B7 /* 0x1800 | topic 0xB7, unused in the v7.0.1 bundle */
#define FAULT_APP_EXIT_CC 1
#define FAULT_APP_PIPE_DEPTH 4
#define FAULT_APP_PIPE_NAME "FAULT_APP_CMD"

typedef struct
{
    CFE_SB_PipeId_t Pipe;
    uint32          RunStatus;
} FAULT_APP_Data_t;

static FAULT_APP_Data_t FAULT_APP_Data;

void FAULT_APP_Main(void)
{
    CFE_Status_t      status;
    CFE_SB_Buffer_t  *buf;
    CFE_MSG_FcnCode_t fcn = 0;

    memset(&FAULT_APP_Data, 0, sizeof(FAULT_APP_Data));
    FAULT_APP_Data.RunStatus = CFE_ES_RunStatus_APP_RUN;

    status = CFE_EVS_Register(NULL, 0, CFE_EVS_EventFilter_BINARY);
    if (status != CFE_SUCCESS)
    {
        CFE_ES_WriteToSysLog("FAULT_APP: EVS register failed, RC = 0x%08lX\n", (unsigned long)status);
        CFE_ES_ExitApp(CFE_ES_RunStatus_APP_ERROR);
    }

    status = CFE_SB_CreatePipe(&FAULT_APP_Data.Pipe, FAULT_APP_PIPE_DEPTH, FAULT_APP_PIPE_NAME);
    if (status != CFE_SUCCESS)
    {
        CFE_ES_WriteToSysLog("FAULT_APP: CreatePipe failed, RC = 0x%08lX\n", (unsigned long)status);
        CFE_ES_ExitApp(CFE_ES_RunStatus_APP_ERROR);
    }

    status = CFE_SB_Subscribe(CFE_SB_ValueToMsgId(FAULT_APP_CMD_MID), FAULT_APP_Data.Pipe);
    if (status != CFE_SUCCESS)
    {
        CFE_ES_WriteToSysLog("FAULT_APP: Subscribe failed, RC = 0x%08lX\n", (unsigned long)status);
        CFE_ES_ExitApp(CFE_ES_RunStatus_APP_ERROR);
    }

    CFE_EVS_SendEvent(1, CFE_EVS_EventType_INFORMATION, "FAULT_APP initialized");

    while (CFE_ES_RunLoop(&FAULT_APP_Data.RunStatus) == true)
    {
        status = CFE_SB_ReceiveBuffer(&buf, FAULT_APP_Data.Pipe, CFE_SB_PEND_FOREVER);
        if (status != CFE_SUCCESS)
        {
            FAULT_APP_Data.RunStatus = CFE_ES_RunStatus_APP_ERROR;
            break;
        }
        CFE_MSG_GetFcnCode(&buf->Msg, &fcn);
        if (fcn == FAULT_APP_EXIT_CC)
        {
            FAULT_APP_Data.RunStatus = CFE_ES_RunStatus_APP_ERROR;
        }
    }

    CFE_ES_ExitApp(FAULT_APP_Data.RunStatus);
}
