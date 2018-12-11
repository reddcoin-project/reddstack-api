## Reddstack API Interface

This package contains the web interface for Reddstack Server. It communicates with the Reddstack server and provides an interface for creating and managing names in a decentralized namespaces and database tables on the blockchain

## Installation
Installing this package and required dependencies

### Debian + Ubuntu

####Install Python 2.7
```
[sudo] apt update
[sudo] apt install python
```

####Install pip
```
[sudo] apt install python-pip
```

####Install virtualenv
```
[sudo] pip install virtualenv
```

###Reddstack-api installation

Create installation directory
```
$ cd ~
$ mkdir reddstack
$ cd reddstack
```

Download the required sources from github

```
$ git clone https://github.com/reddcoin-project/pyreddcoin
$ git clone https://github.com/reddcoin-project/pyreddcointools
$ git clone https://github.com/reddcoin-project/blockstore-client
$ git clone https://github.com/reddcoin-project/reddstack-api
```

Ideally you will install reddstack-api into a virtual environment


```
$ cd ~/reddstack
$ virtualenv venv
$ source venv/bin/activate
```

Install dependencies (from github:)

```
$ cd ~/reddstack/pyreddcointools
$ python setup.py install
$ cd ../pyreddcoin
$ python setup.py install
$ cd ../blockstore-client
$ python setup.py install
```

Install dependencies (via pip:)

```
$ pip install -r requirements.txt
```

This will download the latest internal dependencies to the virtual environment

##Configure reddid server endpoint
Using your preferred text editor
```
$ nano ~/.reddstore-client/reddstore-client.ini
```

```
[blockstore-client]
server = [reddid-server-ip]
port = 6264
advanced_mode = true
```
##Configure local storage
```
$ mkdir /var/blockstore-disk
$ mkdir /var/blockstore-disk/immutable
$ mkdir /var/blockstore-disk/mutable
$ chown -R [user]:[group] /var/blockstore-disk
```
Where [user]:[group] is the user account that you will be running the api service under.

## Usage

Start application

```
$ cd ~/reddstack/reddstack-api/bin
./reddstackapid.py
```

Reddstack-web is listening on all interfaces, port 5000.  
Launch from your favourite browser

```
http://[external-ip]:5000/api/connected
```

