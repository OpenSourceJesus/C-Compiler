#ifdef GCC
#include <stdio.h>
#define print printf
#else
void print(char *fmt, char *msg) {
	/* Empty body - compiler will generate syscall code */
}
#endif

/* Test file demonstrating #include from a subfolder */

#include "math_utils.h"

char successMsg[] = "Success\n";
char failMsg[] = "Fail\n";

int main() {
	volatile int iterations = 1000000;  /* 1 million iterations */
	volatile int result = 0;
	
	/* Loop to test actual execution time, not just startup */
	for (int i = 0; i < iterations; i++) {
		int a = 3;
		int b = 4;
		
		/* square(3) = 9 */
		int sq = square(a);
		
		/* cube(2) = 8 */
		int cb = cube(2);
		
		/* sum_of_squares(3, 4) = 9 + 16 = 25 */
		int sos = sum_of_squares(a, b);
		
		result += sq + cb + sos;
	}
	

	if (result % 256 == 128)
		print("%s", successMsg);
	else
	{
		print("%s", failMsg);
		print("%d", result);
	}
	/* Return result modulo to keep in valid range */
	return result % 256;
}
