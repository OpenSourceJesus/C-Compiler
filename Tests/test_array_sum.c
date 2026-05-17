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

int test_sum (int *a, int length)
{
	int sum = 0;
	for (int i = 0; i < length; i++)
		sum += a[i];
	return sum;
}

int main ()
{
	volatile int iterations = 1000000;
	volatile int last_sum = 0;
	
	int arr[64];
	for (int i = 0; i < 64; i++)
		arr[i] = i;
	/* Loop to test actual execution time, not just startup */
	for (int i = 0; i < iterations; i++)
		last_sum = test_sum(arr, 64);

	if (last_sum == 2016)
		print("%s", successMsg);
	else
	{
		print("%s", failMsg);
		print("%d", last_sum);
	}
	
	return 0;
}