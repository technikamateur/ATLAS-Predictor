CC=gcc
LDFLAGS=-shared
CFLAGS=-fPIC -Iinclude -Wall -Wextra -Wno-unknown-pragmas
HEADERS=llsp.h
RM=rm -r

all: helper.so
clean:
	$(RM) *.so *.o

helper.so: helper.o llsp.o
	$(CC) $(LDFLAGS) $^ -o $@

llsp.o: llsp.c $(HEADERS) Makefile
	$(CC) $(CFLAGS) -c $< -o $@

helper.o: helper.c $(HEADERS) Makefile
	$(CC) $(CFLAGS) -c $< -o $@

.PHONY: clean
