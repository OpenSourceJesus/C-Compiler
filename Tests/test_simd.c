#ifdef GCC
#define int1_t char
#endif
#ifndef GCC
#define int1_t auto _Alignas(8) char
#endif

int1_t a;

int main ()
{
	a = 5000;
	return 0;
}