# movies

simple web app for storing a list of movies you want to see it supports users,
passwords and don't expect much more, no bells and whistles.

## acknowledgement

the authentication part and the data base used is from an open-source project
[tcf][tcf].

## usage 

### how to create a user

So currently if you want to create a user you have to create a directory where
all the user will be stored in the server.

Then (still on the server, and once you `cd` into the repo) you'll do:
```
./ttbd-passwd -p <path to user dir> <username>
```
you'll be prompted to enter a password, and that's it. Simple as that

### container

if you want to use the Containerfile included in the project you have to
create a directory called `users` at the same directory that the Containerfile
is. Then you want to use the `ttbd-passwd` script to create users in that
directory


[tcf]: https://github.com/intel/tcf
