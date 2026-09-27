-- Generated from marketplace/models.py (PostgreSQL dialect). `flask init-db` creates the same schema
-- on any database SQLAlchemy supports, so you normally don't need to run this by hand.

CREATE TABLE setting (
	key VARCHAR(60) NOT NULL, 
	value TEXT NOT NULL, 
	PRIMARY KEY (key)
);

CREATE TABLE "user" (
	id SERIAL NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role VARCHAR(10) NOT NULL, 
	active BOOLEAN NOT NULL, 
	street VARCHAR(200) NOT NULL, 
	city VARCHAR(100) NOT NULL, 
	state VARCHAR(2) NOT NULL, 
	zip VARCHAR(10) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_user_role CHECK (role IN ('customer', 'seller', 'admin')), 
	UNIQUE (email)
);

CREATE TABLE store (
	id SERIAL NOT NULL, 
	owner_id INTEGER NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	description TEXT NOT NULL, 
	active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (owner_id), 
	FOREIGN KEY(owner_id) REFERENCES "user" (id), 
	UNIQUE (name)
);

CREATE TABLE orders (
	id SERIAL NOT NULL, 
	customer_id INTEGER NOT NULL, 
	store_id INTEGER NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	subtotal_cents INTEGER NOT NULL, 
	shipping_cents INTEGER NOT NULL, 
	shipping_service VARCHAR(60) NOT NULL, 
	ship_name VARCHAR(120) NOT NULL, 
	ship_street VARCHAR(200) NOT NULL, 
	ship_city VARCHAR(100) NOT NULL, 
	ship_state VARCHAR(2) NOT NULL, 
	ship_zip VARCHAR(10) NOT NULL, 
	tracking_number VARCHAR(60) NOT NULL, 
	return_reason TEXT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_order_status CHECK (status IN ('placed', 'shipped', 'delivered', 'cancelled', 'return_requested', 'returned', 'return_rejected')), 
	FOREIGN KEY(customer_id) REFERENCES "user" (id), 
	FOREIGN KEY(store_id) REFERENCES store (id)
);

CREATE INDEX ix_orders_status ON orders (status);
CREATE INDEX ix_orders_created_at ON orders (created_at);
CREATE INDEX ix_orders_store_id ON orders (store_id);
CREATE INDEX ix_orders_customer_id ON orders (customer_id);

CREATE TABLE product (
	id SERIAL NOT NULL, 
	store_id INTEGER NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	description TEXT NOT NULL, 
	category VARCHAR(60) NOT NULL, 
	price_cents INTEGER NOT NULL, 
	stock INTEGER NOT NULL, 
	weight_lb DOUBLE PRECISION NOT NULL, 
	length_in DOUBLE PRECISION NOT NULL, 
	width_in DOUBLE PRECISION NOT NULL, 
	height_in DOUBLE PRECISION NOT NULL, 
	image VARCHAR(255), 
	active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_product_price CHECK (price_cents >= 0), 
	CONSTRAINT ck_product_stock CHECK (stock >= 0), 
	CONSTRAINT ck_product_dims CHECK (weight_lb > 0 AND length_in > 0 AND width_in > 0 AND height_in > 0), 
	FOREIGN KEY(store_id) REFERENCES store (id)
);

CREATE INDEX ix_product_category ON product (category);
CREATE INDEX ix_product_store_id ON product (store_id);

CREATE TABLE cart_item (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	product_id INTEGER NOT NULL, 
	quantity INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_cart_line UNIQUE (user_id, product_id), 
	CONSTRAINT ck_cart_qty CHECK (quantity > 0), 
	FOREIGN KEY(user_id) REFERENCES "user" (id), 
	FOREIGN KEY(product_id) REFERENCES product (id)
);

CREATE INDEX ix_cart_item_user_id ON cart_item (user_id);

CREATE TABLE message (
	id SERIAL NOT NULL, 
	sender_id INTEGER NOT NULL, 
	recipient_id INTEGER NOT NULL, 
	product_id INTEGER, 
	order_id INTEGER, 
	body TEXT NOT NULL, 
	read BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(sender_id) REFERENCES "user" (id), 
	FOREIGN KEY(recipient_id) REFERENCES "user" (id), 
	FOREIGN KEY(product_id) REFERENCES product (id), 
	FOREIGN KEY(order_id) REFERENCES orders (id)
);

CREATE INDEX ix_message_sender_id ON message (sender_id);
CREATE INDEX ix_message_recipient_id ON message (recipient_id);

CREATE TABLE order_item (
	id SERIAL NOT NULL, 
	order_id INTEGER NOT NULL, 
	product_id INTEGER NOT NULL, 
	product_name VARCHAR(200) NOT NULL, 
	unit_price_cents INTEGER NOT NULL, 
	quantity INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(order_id) REFERENCES orders (id), 
	FOREIGN KEY(product_id) REFERENCES product (id)
);

CREATE INDEX ix_order_item_order_id ON order_item (order_id);

INSERT INTO setting (key, value) VALUES ('site_name', 'Longhorn Market');
INSERT INTO setting (key, value) VALUES ('commission_pct', '10');
INSERT INTO setting (key, value) VALUES ('announcement', '');
