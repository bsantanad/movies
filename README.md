# movies

simple web app for storing a list of movies you want to see it supports users,
passwords and dont expect much more, no bells and whistles.

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


[tcf]: https://github.com/intel/tcf
