#ifdef GCC
#include <stdio.h>
#define print printf
#else
void print(char *fmt, char *msg) {
	/* Empty body - compiler will generate syscall code */
}
#endif

char successMsg[] = "Success\n";
char failMsg[] = "Fail\n";

/* Test C file for the custom compiler */

int add(int a, int b) {
	return a + b;
}

int multiply(int x, int y) {
	return x * y;
}

int main() {
	volatile int iterations = 1000000;  /* 1 million iterations */
	volatile int result = 0;
	
	/* Loop to test actual execution time, not just startup */
	for (int i = 0; i < iterations; i++) {
		int result1 = add(3, 4);
		int result2 = multiply(5, 6);
		result += result1 + result2;
	}

	if (result % 256 == 64)
		print("%s", successMsg);
	else
	{
		print("%s", failMsg);
		print("%d", result);
	}
	
	return result % 256;  /* Modulo to keep return value in valid range */
}