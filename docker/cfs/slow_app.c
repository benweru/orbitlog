/*
 * Slow consumer used by the sb_pipe_full injector.
 * It owns a depth-4 command pipe and drains it only once every
 * SLOW_APP_DRAIN_MS, so a burst of more than 2 * depth commands sent between
 * drains must overflow the pipe (CFE_SB_Q_FULL_ERR_EID, "Pipe Overflow").
 */
#include "cfe.h"
#include "cfe_msg.h"

#define SLOW_APP_CMD_MID 0x18B9 /* 0x1800 | topic 0xB9, unused in the v7.0.1 bundle */
#define SLOW_APP_PIPE_DEPTH 4
#define SLOW_APP_PIPE_NAME "SLOW_APP_CMD"
#define SLOW_APP_DRAIN_MS 5000
#define SLOW_APP_MSG_LIMIT 64

static CFE_SB_PipeId_t SLOW_APP_Pipe;

void SLOW_APP_Main(void)
{
    CFE_Status_t     status;
    CFE_SB_Buffer_t *buf;
    uint32           run_status = CFE_ES_RunStatus_APP_RUN;

    status = CFE_EVS_Register(NULL, 0, CFE_EVS_EventFilter_BINARY);
    if (status != CFE_SUCCESS)
    {
        CFE_ES_WriteToSysLog("SLOW_APP: EVS register failed, RC = 0x%08lX\n", (unsigned long)status);
        CFE_ES_ExitApp(CFE_ES_RunStatus_APP_ERROR);
    }

    status = CFE_SB_CreatePipe(&SLOW_APP_Pipe, SLOW_APP_PIPE_DEPTH, SLOW_APP_PIPE_NAME);
    if (status != CFE_SUCCESS)
    {
        CFE_ES_WriteToSysLog("SLOW_APP: CreatePipe failed, RC = 0x%08lX\n", (unsigned long)status);
        CFE_ES_ExitApp(CFE_ES_RunStatus_APP_ERROR);
    }

    /* The default per-subscription limit (4) would reject the burst with
     * Msg Limit Err before the pipe itself fills. */
    status = CFE_SB_SubscribeEx(CFE_SB_ValueToMsgId(SLOW_APP_CMD_MID), SLOW_APP_Pipe, CFE_SB_DEFAULT_QOS,
                                SLOW_APP_MSG_LIMIT);
    if (status != CFE_SUCCESS)
    {
        CFE_ES_WriteToSysLog("SLOW_APP: Subscribe failed, RC = 0x%08lX\n", (unsigned long)status);
        CFE_ES_ExitApp(CFE_ES_RunStatus_APP_ERROR);
    }

    CFE_EVS_SendEvent(1, CFE_EVS_EventType_INFORMATION, "SLOW_APP initialized, pipe depth %d, drain every %d ms",
                      SLOW_APP_PIPE_DEPTH, SLOW_APP_DRAIN_MS);

    while (CFE_ES_RunLoop(&run_status) == true)
    {
        OS_TaskDelay(SLOW_APP_DRAIN_MS);
        while (CFE_SB_ReceiveBuffer(&buf, SLOW_APP_Pipe, CFE_SB_POLL) == CFE_SUCCESS)
        {
        }
    }

    CFE_ES_ExitApp(run_status);
}
