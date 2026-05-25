#ifdef GCC
#include <stdio.h>
#define print printf
#else
void print(char *fmt, char *msg) {
	/* Empty body - compiler will generate syscall code */
}
#endif

void test ()
{
	print("Called function\n");
}

int main ()
{
	volatile int iterations = 1000000;  /* 1 million iterations */
	
	/* Loop to test actual execution time, not just startup */
	for (int i = 0; i < iterations; i++) {
		test ();
	}
	
	print("Reached end\n");
	return 0;
}