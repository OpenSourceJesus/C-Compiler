/* Test that prints 'Hello World!' using a syscall without any #include */

/* String constant for "Hello World!\n" */
char msg[] = "Hello World!\n";

/* Function to make write syscall - compiler will detect this pattern and generate syscall code */
void sys_write(int fd, char *buf, int len) {
    /* Empty body - compiler will generate syscall code */
}

int main() {
    sys_write(1, msg, 13);  /* 1 = stdout, msg = string, 13 = length */
    return 0;
}
