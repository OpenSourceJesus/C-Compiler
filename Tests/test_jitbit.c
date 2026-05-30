#ifdef GCC
#include <stdio.h>
#define print printf
#else
void print(char *fmt, char *msg) {
	/* Empty body - compiler will generate syscall code */
}
#endif
#include <stdint.h>
#include <stddef.h>

typedef uint8_t T;

static T test_arr[64];
static T *A;
static size_t A_len;
static int64_t rax;

static void sum (void)
{
	/* assert A_len >= 32; */
	/* assert A_len % 32 == 0; */
	for (size_t i = 0; i < A_len; i ++)
	{
		int64_t rbx = A[i];
		rax += rbx;
	}
}

static void foo (void)
{
	sum ();
}

static void bar (void)
{
	foo ();
	sum ();
}

static void boo (void)
{
	bar ();
	sum ();
}

static void zoo (void)
{
	boo ();
	sum ();
}

static void main_fn (void)
{
	rax = 0;
	foo ();
	bar ();
	boo ();
	zoo ();
}

int64_t main (void)
{
	for (size_t i = 0; i < 64; i ++)
		test_arr[i] = (T) i;
	A = test_arr;
	A_len = 64;
	main_fn ();
	print("%s", "Reached end\n");
	return rax;
}