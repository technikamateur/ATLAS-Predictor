CC=gcc
CFLAGS=-fPIC -shared -Iinclude
HEADERS=llsp.h
RM=rm -r

all: helper.so
clean:
	$(RM) *.so
helper.so: helper.c llsp.c $(HEADERS)
	$(CC) $(CFLAGS) $^ -o $@
