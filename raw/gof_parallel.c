#include <omp.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>
#include <string.h>
#include <getopt.h>
#include <pthread.h>

/*
  typedef enum omp_sched_t {
    omp_sched_static = 1,
    omp_sched_dynamic = 2,
    omp_sched_guided = 3,
    omp_sched_auto = 4
  } omp_sched_t;
*/

// defaults
static int repetitions = 100;
static u_int64_t columns = 128;
static u_int64_t rows = 128;
static u_int8_t show_progress = 0;
static u_int8_t produce_output = 0;
static char output_fname[255] = "life_";
// getopt
static struct option long_options[] =
        {
                {"execution",   optional_argument, NULL, 'e'},
                {"help",        optional_argument, NULL, 'h'},
                {"output",      optional_argument, NULL, 'o'},
                {"progress",    optional_argument, NULL, 'p'},
                {"repetitions", optional_argument, NULL, 'R'},
                {"size",        optional_argument, NULL, 's'},
                {NULL,          0,                 NULL, 0}};

void field_initializer(u_int8_t *state) {
    //fills fields with random numbers 0 = dead, 1 = alive
#pragma omp parallel
    {
        unsigned tid = pthread_self();
        unsigned seed = time(0) + tid;
#pragma omp parallel for schedule(runtime)
        for (int i = 0; i < columns * rows; i++) {
            state[i] = rand_r(&seed) % 2;
        }
    }
    return;
}

void calculate_corners(u_int8_t *state, u_int8_t *state_old) {
    u_int8_t corner_sum = 0;
    // top left
    corner_sum = state_old[1] +
                 state_old[columns] +
                 state_old[columns + 1] +
                 state_old[(rows - 1) * columns] +
                 state_old[(rows - 1) * columns + 1] +
                 state_old[columns - 1] +
                 state_old[2 * columns - 1] +
                 state_old[rows * columns - 1];
    state[0] = (corner_sum == 3) | ((corner_sum == 2) & state_old[0]);
    // top right
    corner_sum = state_old[columns - 2] +
                 state_old[2 * columns - 1] +
                 state_old[2 * columns - 2] +
                 state_old[rows * columns - 1] +
                 state_old[rows * columns - 2] +
                 state_old[0] +
                 state_old[columns] +
                 state_old[(rows - 1) * columns];
    state[columns - 1] = (corner_sum == 3) | ((corner_sum == 2) & state_old[columns - 1]);
    // bottom left
    corner_sum = state_old[(rows - 2) * columns] +
                 state_old[(rows - 2) * columns + 1] +
                 state_old[(rows - 1) * columns + 1] +
                 state_old[0] +
                 state_old[1] +
                 state_old[columns - 1] +
                 state_old[(rows - 1) * columns - 1] +
                 state_old[(rows * columns - 1)];
    state[(rows - 1) * columns] = (corner_sum == 3) | ((corner_sum == 2) & state_old[(rows - 1) * columns]);
    // bottom right
    corner_sum = state_old[0] +
                 state_old[columns - 1] +
                 state_old[columns - 2] +
                 state_old[(rows - 2) * columns] +
                 state_old[(rows - 1) * columns] +
                 state_old[(rows - 1) * columns - 1] +
                 state_old[(rows - 1) * columns - 2] +
                 state_old[(rows * columns - 2)];
    state[rows * columns - 1] = (corner_sum == 3) | ((corner_sum == 2) & state_old[rows * columns - 1]);
}

void calculate_left_right(u_int8_t *state, u_int8_t *state_old) {
#pragma omp parallel for schedule(runtime)
    for (int i = 1; i < rows - 1; i++) {
        u_int8_t sum_of_l_edge = state_old[i * columns + 1] +
                                 state_old[(i - 1) * columns] +
                                 state_old[(i - 1) * columns + 1] +
                                 state_old[(i + 1) * columns] +
                                 state_old[(i + 1) * columns + 1] +
                                 state_old[i * columns - 1] +
                                 state_old[(i + 1) * columns - 1] +
                                 state_old[(i + 2) * columns - 1];
        state[i * columns] = (sum_of_l_edge == 3) | ((sum_of_l_edge == 2) & state_old[i * columns]);
        u_int8_t sum_of_r_edge = state_old[(i + 1) * columns - 2] +
                                 state_old[i * columns - 2] +
                                 state_old[i * columns - 1] +
                                 state_old[(i + 2) * columns - 2] +
                                 state_old[(i + 2) * columns - 1] +
                                 state_old[(i - 1) * columns] +
                                 state_old[i * columns] +
                                 state_old[(i + 1) * columns];
        state[(i + 1) * columns - 1] = (sum_of_r_edge == 3) | ((sum_of_r_edge == 2) & state_old[(i + 1) * columns - 1]);
    }
}

void calculate_top_bottom(u_int8_t *state, u_int8_t *state_old) {
#pragma omp parallel for schedule(runtime)
    for (int i = 1; i < columns - 1; i++) {
        u_int8_t sum_of_t_edge = state_old[i - 1] +
                                 state_old[i + 1] +
                                 state_old[2 * columns + (i - 1)] +
                                 state_old[2 * columns + i] +
                                 state_old[2 * columns + (i + 1)] +
                                 state_old[(rows - 1) * columns + i] +
                                 state_old[(rows - 1) * columns + i + 1] +
                                 state_old[(rows - 1) * columns + i - 1];
        state[i] = (sum_of_t_edge == 3) | ((sum_of_t_edge == 2) & state_old[i]);
        u_int8_t sum_of_b_edge = state_old[(rows - 1) * columns + (i - 1)] +
                                 state_old[(rows - 1) * columns + (i + 1)] +
                                 state_old[(rows - 2) * columns + (i - 1)] +
                                 state_old[(rows - 2) * columns + i] +
                                 state_old[(rows - 2) * columns + (i + 1)] +
                                 state_old[i] +
                                 state_old[i - 1] +
                                 state_old[i + 1];
        state[(rows - 1) * columns + i] =
                (sum_of_b_edge == 3) | ((sum_of_b_edge == 2) & state_old[(rows - 1) * columns + i]);
    }
}

void calculate_next_gen(u_int8_t *state, u_int8_t *state_old) {
    //i = row, j = column

    // corners
    calculate_corners(state, state_old);
    // left and right edge
    calculate_left_right(state, state_old);
    // top and bottom edge
    calculate_top_bottom(state, state_old);
    // middle
#pragma omp parallel for schedule(runtime)
    for (int i = 1; i < rows - 1; i++) {
        for (int j = 1; j < columns - 1; j++) {
            //count up a number (8)
            u_int8_t sum_of_8 = state_old[(i - 1) * columns + (j - 1)] +
                                state_old[(i - 1) * columns + j] +
                                state_old[(i - 1) * columns + (j + 1)] +
                                state_old[i * columns + (j - 1)] +
                                state_old[i * columns + (j + 1)] +
                                state_old[(i + 1) * columns + (j - 1)] +
                                state_old[(i + 1) * columns + j] +
                                state_old[(i + 1) * columns + (j + 1)];
            state[i * columns + j] = (sum_of_8 == 3) | ((sum_of_8 == 2) & state_old[i * columns + j]);
        }
    }
    return;
}

void write_pbm_file(u_int8_t *state, int i) {
    FILE *fptr;
    char new_filename[65];
    sprintf(new_filename, "%s%06d.pbm", output_fname, i);
    fptr = fopen(new_filename, "w");
    fprintf(fptr, "P1\n");
    fprintf(fptr, "# This is the %06d result. Have fun :)\n", i);
    fprintf(fptr, "%lu %lu\n", columns, rows);
    for (int i = 0; i < rows; i++) {
        for (int j = 0; j < columns; j++) {
            fprintf(fptr, "%d ", state[i * columns + j]);
        }
        fprintf(fptr, "\n");
    }
    fclose(fptr);
    return;
}


void argments(int argc, char *argv[]) {
    int opt;
    while ((opt = getopt_long(argc, argv, "hpe:R:s:o:", long_options, NULL)) != -1) {
        switch (opt) {
            case 'e':
                switch (atoi(optarg)) {
                    case 1:
                        omp_set_schedule(omp_sched_static, 1);
                        break;
                    case 2:
                        omp_set_schedule(omp_sched_dynamic, 1);
                        break;
                    case 3:
                        omp_set_schedule(omp_sched_guided, 1);
                        break;
                    default:
                        omp_set_schedule(omp_sched_auto, 1);
                        break;
                }
                break;
            case 'R':
                if (strlen(optarg) > 254) {
                    printf("Given repetitions too large.\n");
                    exit(1);
                }
                repetitions = atoi(optarg);
                break;
            case 'o':
                printf("%s", optarg);
                if (strlen(optarg) > 254) {
                    printf("Output filename too big.\n");
                    exit(1);
                }
                sprintf(output_fname, "%s", optarg);
                produce_output = 1;
                break;
            case 'p':
                show_progress = 1;
                break;
            case 's':
                if (strlen(optarg) > 254) {
                    printf("Given size too large.\n");
                    exit(1);
                }
                char size[255];
                sprintf(size, "%s", optarg);
                char *word = strtok(size, ",");
                columns = strtol(word, NULL, 10);
                word = strtok(NULL, ",");
                rows = strtol(word, NULL, 10);
                break;
            case 'h':
                printf("Welcome to the game of life!\nAvailable arguments:\n");
                printf("-e, --execution [int]      default: auto; Scheduler information: 1=static, 2=dynamic, 3=guided\n");
                printf("-h, --help                 prints this help page and exits\n");
                printf("-o, --output [filename]    default: life_xxxxxx.pbm, provide an output filename\n");
                printf("-p, --progress             default: false; prints progress on terminal\n");
                printf("-R, --repetitions [int]    default: 3 repetitions; specifies the number of images created\n");
                printf("-s, --size <columns,rows>  default: 128x128; specifies the number of columns and rows\n");
                exit(0);
        }
    }
    return;
}

int main(int argc, char *argv[]) {
    // arguments
    argments(argc, argv);
    // welcome information
    printf("Welcome to the game of life!\n");
    // ignore output if no thread limit is specified
    printf("We are doing %d repetitions with %d thread(s)!\n", repetitions, omp_get_thread_limit());
    printf("Game size: Columns: %lu, Rows: %lu.\n", columns, rows);
    printf("Starting now...\n");
    // initializing states and pointers
    u_int8_t *state_1 = (u_int8_t *) malloc(columns * rows * sizeof(u_int8_t));
    u_int8_t *state_2 = (u_int8_t *) malloc(columns * rows * sizeof(u_int8_t));
    u_int8_t *state_in = state_1;
    u_int8_t *state_out = state_2;
    u_int8_t *state_tmp = NULL;
    // starting clock
    clock_t t;
    double time_rand = 0;
    double time_calc = 0;
    double time_out = 0;
    double t_omp = 0;
    double omp_rand = 0;
    double omp_calc = 0;
    // filling with random numbers
    t = clock();
    t_omp = omp_get_wtime();
    field_initializer(state_1);
    omp_rand = omp_get_wtime() - t_omp;
    t = clock() - t;
    time_rand = ((double) t) / CLOCKS_PER_SEC; // in seconds
    // write random pattern as -1 file
    if (produce_output) {
        t = clock();
        write_pbm_file(state_in, -1);
        t = clock() - t;
        time_out += ((double) t) / CLOCKS_PER_SEC;
    }
    //calculation
    for (int i = 0; i < repetitions; i++) {
        t = clock();
        t_omp = omp_get_wtime();
        calculate_next_gen(state_out, state_in);
        t_omp = omp_get_wtime() - t_omp;
        t = clock() - t;
        omp_calc += t_omp;
        time_calc += ((double) t) / CLOCKS_PER_SEC;
        state_tmp = state_in;
        state_in = state_out;
        state_out = state_tmp;
        if (show_progress) {
            double percentage = 100.0 * (i + 1) / repetitions;
            printf("%.1lf%c\n", percentage, 37);
        }
        if (produce_output) {
            t = clock();
            write_pbm_file(state_in, i);
            t = clock() - t;
            time_out += ((double) t) / CLOCKS_PER_SEC;
        }
    }
    printf("Field initializer took %f seconds to execute (all threads added).\n", time_rand);
    printf("Field initializer took %f seconds to execute (real time).\n", omp_rand);
    printf("Calculation took %f seconds to execute (all threads added).\n", time_calc);
    printf("Calculation took %f seconds to execute (real time).\n", omp_calc);
    printf("Writing pbm files took %f seconds to execute.\n", time_out);
    printf("Done :)\n");
    exit(0);
}