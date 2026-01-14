/* Wrapper header for pycparser to handle GCC extensions */
#ifndef PYPARSER_WRAPPER_H
#define PYPARSER_WRAPPER_H

/* Define __attribute__ as empty variadic macro */
#define __attribute__(...) 

/* Handle inline assembly - remove asm keyword entirely
 * Note: This will cause "asm volatile(...)" to become "volatile(...)"
 * which pycparser can't parse. We need to handle this at the source level
 * or use a different approach.
 */
#define asm 
#define __asm__ 
#define __asm 

/* Other GCC extensions */
#define __extension__

#endif /* PYPARSER_WRAPPER_H */
