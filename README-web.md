# Piston.WEB

piston.web serves as a standalone application that everyone can run on
its home computer. The only connection opened is to the API node that
provides access to the STEEM network.

## Installation

Required dependencies:

    apt-get update
    apt-get install -y git make gcc libssl-dev libgmp-dev python-dev libxml2-dev libxslt1-dev zlib1g-dev libyaml

Obtain the piston sources

    git clone https://github.com/xeroc/piston/
    # install the python dependencies
    pip install -r requirements-web.txt
    make install-user

[Install the steem GUI on Windows 7](https://steemit.com/piston/@etz/piston-web-install-a-steem-gui-on-windows-7) (thanks @etz)

## Usage
    
    piston web

On first run, you will be asked to provide a passphrase for your new
wallet. Empty password are allowed but result in private keys being
stored in plain text.

After that, you will see

     * Running on http://127.0.0.1:5054/ (Press CTRL+C to quit)
     * Restarting with stat
     * Debugger is active!
     * Debugger pin code: 227-869-909

Ignore the debugging output and start using piston.web in your browser
by accessing

    http://127.0.0.1:5054/

NOTE: piston.web will only be reachable from the same machine
(localhost).

## Technologies

### Backend

The backend is written in python using

* Flask (with Jinja2)
* python-steem.

It offers the HTML files and a Socket-IO for real-time communications.

### Frontend

These technologies have been used so far in piston.web:

* Bootstrap
* Markdown
* Fontawesome
* Plain Javascript

### Wallet

The wallet is only accessible from the backend. All keys are encrypted
with a random master password that is stored in an SQLite3 database in its
AES encrypted form. Each private key is encrypted with the master password
using BIP32 and stored in a SQLite3 database.
The wallet will make backups of the SQLite3 database every week and keep
several weeks of backup.

# IMPORTANT NOTE

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
    THE SOFTWARE.
