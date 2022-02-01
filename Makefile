CC = gcc
CFLAGS = -fPIC -shared -Iinclude
HEADERS = llsp.h

helper: helper.c llsp.c $(HEADERS)
	$(CC) $(CFLAGS) -o helper.so helper.c llsp.c