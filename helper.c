#include "llsp.h"

llsp_t *predictor;
size_t metric_size;

void initialize(size_t count) {
    predictor = llsp_new(count);
    metric_size = count;
    return;
}

void add(double metric[metric_size], double target) {
    llsp_add(predictor, metric, target);
    return;
}

int solve(){
    double* result = llsp_solve(predictor);
    if (result == NULL) {
        return 0;
    } else {
        return 1;
    }
}

double predict(double metric[metric_size]) {
    double result = llsp_predict(predictor, metric);
    return result;
}