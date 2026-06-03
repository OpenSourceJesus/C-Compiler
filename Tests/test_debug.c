#ifdef GCC
#include <stdio.h>
#define print printf
#else
void print(char *fmt, char *msg) {
	/* Empty body - compiler will generate syscall code */
}
#endif

int main ()
{
	// MEMDUMP RAX = 0x0 RSI = 0x1
	print("Reached end\n");
	return 0;
}