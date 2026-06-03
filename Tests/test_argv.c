/* Verify main(int argc, char *argv[]) receives the Linux argc/argv layout. */

#ifdef GCC
#include <stdio.h>
#define print printf
#else
void print(char *fmt, char *msg) {
	/* Empty body - compiler will generate syscall code */
}
#endif

int main(int argc, char *argv[]) {
	if (argc < 1 || argv[0] == 0)
		return 1;

	/* argv[0] is always the program name when argc/argv are set up correctly. */
	if (argv[0][0] == '\0')
		return 2;

	/* When an extra argument is supplied (e.g. benchmark.py test_argv.c 42), verify it. */
	if (argc >= 2) {
		if (argv[1][0] != '4' || argv[1][1] != '2' || argv[1][2] != '\0')
			return 3;
		print("argv ok\n");
	}

	return 0;
}
