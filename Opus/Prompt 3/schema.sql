-- Generated from models.py (PostgreSQL dialect). `flask --app app init-db` creates this for you.

CREATE TABLE setting (
	key VARCHAR(50) NOT NULL, 
	value VARCHAR(200) NOT NULL, 
	PRIMARY KEY (key)
);


CREATE TABLE "user" (
	id SERIAL NOT NULL, 
	email VARCHAR(254) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	role VARCHAR(10) NOT NULL, 
	active BOOLEAN NOT NULL, 
	street VARCHAR(200), 
	city VARCHAR(100), 
	state VARCHAR(2), 
	zip VARCHAR(5), 
	created_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CHECK (role IN ('customer', 'seller', 'admin'))
);

CREATE UNIQUE INDEX ix_user_email ON "user" (email);

CREATE TABLE store (
	id SERIAL NOT NULL, 
	owner_id INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	description TEXT, 
	active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (owner_id), 
	FOREIGN KEY(owner_id) REFERENCES "user" (id), 
	UNIQUE (name)
);


CREATE TABLE "order" (
	id SERIAL NOT NULL, 
	customer_id INTEGER NOT NULL, 
	store_id INTEGER NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	subtotal_cents INTEGER NOT NULL, 
	shipping_cents INTEGER NOT NULL, 
	total_cents INTEGER NOT NULL, 
	ship_service VARCHAR(20) NOT NULL, 
	ship_name VARCHAR(100) NOT NULL, 
	ship_street VARCHAR(200) NOT NULL, 
	ship_city VARCHAR(100) NOT NULL, 
	ship_state VARCHAR(2) NOT NULL, 
	ship_zip VARCHAR(5) NOT NULL, 
	tracking VARCHAR(40), 
	return_reason TEXT, 
	created_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CHECK (status IN ('placed', 'shipped', 'delivered', 'return_requested', 'returned', 'cancelled')), 
	FOREIGN KEY(customer_id) REFERENCES "user" (id), 
	FOREIGN KEY(store_id) REFERENCES store (id)
);

CREATE INDEX ix_order_created_at ON "order" (created_at);
CREATE INDEX ix_order_customer_id ON "order" (customer_id);
CREATE INDEX ix_order_store_id ON "order" (store_id);

CREATE TABLE product (
	id SERIAL NOT NULL, 
	store_id INTEGER NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	description TEXT, 
	price_cents INTEGER NOT NULL, 
	stock INTEGER NOT NULL, 
	weight_lb FLOAT NOT NULL, 
	length_in FLOAT NOT NULL, 
	width_in FLOAT NOT NULL, 
	height_in FLOAT NOT NULL, 
	image VARCHAR(64), 
	active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CHECK (price_cents >= 0), 
	CHECK (stock >= 0), 
	CHECK (weight_lb > 0), 
	FOREIGN KEY(store_id) REFERENCES store (id)
);

CREATE INDEX ix_product_store_id ON product (store_id);

CREATE TABLE message (
	id SERIAL NOT NULL, 
	sender_id INTEGER NOT NULL, 
	recipient_id INTEGER NOT NULL, 
	product_id INTEGER, 
	order_id INTEGER, 
	body TEXT NOT NULL, 
	read BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(sender_id) REFERENCES "user" (id), 
	FOREIGN KEY(recipient_id) REFERENCES "user" (id), 
	FOREIGN KEY(product_id) REFERENCES product (id), 
	FOREIGN KEY(order_id) REFERENCES "order" (id)
);

CREATE INDEX ix_message_recipient_id ON message (recipient_id);
CREATE INDEX ix_message_sender_id ON message (sender_id);

CREATE TABLE order_item (
	id SERIAL NOT NULL, 
	order_id INTEGER NOT NULL, 
	product_id INTEGER NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	price_cents INTEGER NOT NULL, 
	quantity INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (quantity > 0), 
	FOREIGN KEY(order_id) REFERENCES "order" (id), 
	FOREIGN KEY(product_id) REFERENCES product (id)
);

CREATE INDEX ix_order_item_order_id ON order_item (order_id);
