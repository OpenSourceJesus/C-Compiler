/* Test file demonstrating #include from a subfolder */

#include "math_utils.h"

int main() {
    int a = 3;
    int b = 4;
    
    /* square(3) = 9 */
    int sq = square(a);
    
    /* cube(2) = 8 */
    int cb = cube(2);
    
    /* sum_of_squares(3, 4) = 9 + 16 = 25 */
    int sos = sum_of_squares(a, b);
    
    /* Return 9 + 8 + 25 = 42 */
    return sq + cb + sos;
}
