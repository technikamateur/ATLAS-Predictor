#include "llsp.h"

llsp_t *predictor;

void initialize(size_t count) {
    predictor = llsp_new(count);
    return;
}