/* Test C file for the custom compiler */

int add(int a, int b) {
    return a + b;
}

int multiply(int x, int y) {
    return x * y;
}

int main() {
    int result1 = add(3, 4);
    int result2 = multiply(5, 6);
    return result1 + result2;
}