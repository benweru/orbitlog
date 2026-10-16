/* Send N identical SAMPLE_APP NOOP commands to ci_lab on localhost.
 * Running inside the container avoids the Docker UDP proxy dropping the burst.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <arpa/inet.h>
#include <sys/socket.h>

int main(int argc, char **argv)
{
    int n;
    int sock;
    int i;
    struct sockaddr_in addr;
    unsigned char pkt[8];
    unsigned char sum;

    if (argc != 2)
    {
        return 2;
    }
    n = atoi(argv[1]);
    if (n < 1)
    {
        return 2;
    }

    /* MsgId 0x1882, unsegmented, length 1, function code 0. Checksum filled below. */
    pkt[0] = 0x18;
    pkt[1] = 0x82;
    pkt[2] = 0xC0;
    pkt[3] = 0x00;
    pkt[4] = 0x00;
    pkt[5] = 0x01;
    pkt[6] = 0x00;
    pkt[7] = 0x00;
    sum = 0xFF;
    for (i = 0; i < 8; i++)
    {
        sum ^= pkt[i];
    }
    pkt[7] = sum;

    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0)
    {
        return 1;
    }
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(1234);
    addr.sin_addr.s_addr = htonl(0x7F000001);
    for (i = 0; i < n; i++)
    {
        if (sendto(sock, pkt, sizeof(pkt), 0, (struct sockaddr *)&addr, sizeof(addr)) < 0)
        {
            return 1;
        }
    }
    return 0;
}
