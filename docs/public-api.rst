****************************
Public API this.piston.rocks
****************************

this.piston.rocks
#################

The public API node at ``this.piston.rocks`` serves as an *experimental endpoint*. It is offered for free to our best efforts.

You may

* use it for prototyping of your tools
* use it for testing

You may not:

* expect it to be reliable
* spam it with unnecessary load

Running your own node
#####################

You can run a similar node with rather low efforts assuming you know how to compile the `official steem daemon <https://github.com/steemit/steem/>`_

Steemd Node
~~~~~~~~~~~

This is the ``config.ini`` file for steemd:

::

      rpc-endpoint = 127.0.0.1:5090

      seed-node=52.38.66.234:2001
      seed-node=52.37.169.52:2001
      seed-node=52.26.78.244:2001
      seed-node=192.99.4.226:2001
      seed-node=46.252.27.1:1337
      seed-node=81.89.101.133:2001
      seed-node=52.4.250.181:39705
      seed-node=85.214.65.220:2001
      seed-node=104.199.157.70:2001
      seed-node=104.236.82.250:2001
      seed-node=104.168.154.160:40696
      seed-node=162.213.199.171:34191
      seed-node=seed.steemed.net:2001
      seed-node=steem.clawmap.com:2001
      seed-node=seed.steemwitness.com:2001
      seed-node=steem-seed1.abit-more.com:2001

      enable-plugin = account_history
      enable-plugin = follow
      enable-plugin = market_history
      enable-plugin = private_message
      enable-plugin = tags

      public-api = database_api login_api market_history_api tag_api follow_api

This opens up the port ``5090`` for localhost. Going forward, you can either open up this port directly to the public, or tunnel it through a webserver (such as nginx) to add SSL on top, do load balancing, throttling etc.

Nginx Webserver
~~~~~~~~~~~~~~~

``this.piston.rocks`` uses a nginx server to 

* provide a readable websocket url
* provide SSL encryption
* perform throttling
* allow load balancing

The configuration would look like this

::

   upstream websockets {       # load balancing two nodes
           server 127.0.0.1:5090;
           server 127.0.0.1:5091;
   }

   server {
       listen 443 ssl;
       server_name this.piston.rocks;
       root /var/www/html/;

       keepalive_timeout 65;
       keepalive_requests 100000;
       sendfile on;
       tcp_nopush on;
       tcp_nodelay on;

       ssl_certificate /etc/letsencrypt/live/this.piston.rocks/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/this.piston.rocks/privkey.pem;
       ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
       ssl_prefer_server_ciphers on;
       ssl_dhparam /etc/ssl/certs/dhparam.pem;
       ssl_ciphers 'ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-DSS-AES128-GCM-SHA256:kEDH+AESGCM:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA:ECDHE-ECDSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-DSS-AES128-SHA256:DHE-RSA-AES256-SHA256:DHE-DSS-AES256-SHA:DHE-RSA-AES256-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:AES:CAMELLIA:DES-CBC3-SHA:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!aECDH:!EDH-DSS-DES-CBC3-SHA:!EDH-RSA-DES-CBC3-SHA:!KRB5-DES-CBC3-SHA';
       ssl_session_timeout 1d;
       ssl_session_cache shared:SSL:50m;
       ssl_stapling on;
       ssl_stapling_verify on;
       add_header Strict-Transport-Security max-age=15768000;

       location ~ ^(/|/ws) {
           limit_req zone=ws burst=5;
           access_log off;
           proxy_pass http://websockets;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header Host $host;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_next_upstream     error timeout invalid_header http_500;
           proxy_connect_timeout   2;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
       }

       location ~ /.well-known {
           allow all;
       }

   }

As you can see from the ``upstream`` block, the node actually uses a load balancing and failover across **two** locally running ``steemd`` nodes.
This allows to upgrade the code and reply one one while the other takes over the full traffic, and vise versa.

