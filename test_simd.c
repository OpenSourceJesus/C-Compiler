/* Test file for SIMD bit-packing and zero-latency kernel access */

// Global variables that will be packed into SIMD register (1-7 bits)
// Using naming convention: _Nbit suffix indicates bit-width for packing

// 1-bit flags (kernel flags for zero-latency access)
char kernel_enabled_1bit;
char interrupt_pending_1bit;
char scheduler_active_1bit;

// 3-bit counter
char task_priority_3bit;

// 4-bit status
char device_status_4bit;

// 5-bit counter
char event_count_5bit;

// Regular global variable (not packed, standard int)
int regular_counter;

// Interrupt callback function - uses zero-latency SIMD register access
void isr_timer_handler() {
    // Zero-latency access to kernel flags via SIMD register
    // No memory reads that could stall the pipeline
    if (kernel_enabled_1bit) {
        if (interrupt_pending_1bit) {
            task_priority_3bit = 3;  // Zero-latency write
            device_status_4bit = 5;  // Zero-latency write
        }
    }
    
    event_count_5bit = event_count_5bit + 1;  // Zero-latency read and write
}

// Regular function
int main() {
    kernel_enabled_1bit = 1;
    interrupt_pending_1bit = 0;
    scheduler_active_1bit = 1;
    task_priority_3bit = 2;
    device_status_4bit = 1;
    event_count_5bit = 0;
    
    regular_counter = 100;  // Regular memory access
    
    return 0;
}
