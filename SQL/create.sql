CREATE TABLE books (
    id SERIAL PRIMARY KEY,
    isbn VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    author VARCHAR NOT NULL,
    year INTEGER
);

CREATE TABLE reviews (
    id SERIAL PRIMARY KEY,
    review VARCHAR NOT NULL,
    books_id INTEGER REFERENCES books,
    users_id INTEGER REFERENCES users
);
