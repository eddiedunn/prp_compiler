# Knowledge Base: Modern Rust Best Practices

## 1. Project Structure with Cargo

Cargo is Rust's built-in build tool and package manager. A standard library or binary project (a "crate") is simple:

```
my_crate/
├── src/
│   └── lib.rs  # or main.rs for a binary
├── tests/
│   └── integration_test.rs
├── benches/
│   └── benchmark.rs
├── Cargo.toml
└── README.md
```

- **`Cargo.toml`**: The manifest file. Defines project metadata, dependencies, and profiles.
- **`src/`**: Contains all the source code.
- **Workspaces**: For larger projects, use Cargo Workspaces to manage multiple related crates in one repository.

```
my_workspace/
├── Cargo.toml  # Defines the workspace members
├── crate_one/
│   ├── src/lib.rs
│   └── Cargo.toml
└── crate_two/
    ├── src/main.rs
    └── Cargo.toml
```

## 2. Dependency Management

Dependencies are managed in `Cargo.toml`.

```toml
[dependencies]
serde = { version = "1.0", features = ["derive"] }
tokio = { version = "1", features = ["full"] }

[dev-dependencies]
# Dependencies only for tests and benchmarks
anyhow = "1.0"
```

- **`cargo build`**: Fetches and builds dependencies.
- **`cargo update`**: Updates dependencies to the latest allowed versions according to semantic versioning.
- **`cargo tree`**: Displays a tree of all dependencies.

## 3. Testing with `cargo test` and `nextest`

Rust has built-in support for unit, integration, and documentation tests.

- **Unit Tests**: Co-located in the `src/` files within a `#[cfg(test)]` module.
- **Integration Tests**: Placed in the `tests/` directory. Each file is a separate integration test crate.
- **`nextest`**: A modern, faster test runner. Install with `cargo install cargo-nextest`. Run tests with `cargo nextest run`.

## 4. Code Quality with `clippy` and `rustfmt`

- **`clippy`**: An official and comprehensive linter that catches common mistakes and suggests improvements. Run with `cargo clippy`.
- **`rustfmt`**: An automatic code formatter that enforces a consistent style across the community. Run with `cargo fmt`.

Configure these tools in your project if needed, but the defaults are excellent.

## 5. Error Handling

The preferred way to handle recoverable errors is with the `Result<T, E>` enum.

- **`Result<T, E>`**: Represents either success (`Ok(T)`) or failure (`Err(E)`).
- **The `?` operator**: Propagates errors up the call stack, reducing boilerplate.

```rust
use std::fs::File;
use std::io::{self, Read};

fn read_username_from_file() -> Result<String, io::Error> {
    let mut s = String::new();
    // The '?' operator will return the Err if File::open fails.
    File::open("hello.txt")?.read_to_string(&mut s)?;
    Ok(s)
}
```

- For unrecoverable errors, use the `panic!` macro, but this should be rare in library code.
- The `anyhow` and `thiserror` crates are highly recommended for more ergonomic error handling in applications.

## 6. Concurrency with `async/await` and Tokio

Rust's ownership model provides strong compile-time guarantees against data races.

- **`async/await`**: The modern syntax for writing asynchronous, non-blocking code.
- **`Tokio`**: The most popular asynchronous runtime for Rust. It provides the executor, I/O primitives (TCP, UDP, files), and task management.

```rust
use tokio::time::{sleep, Duration};

#[tokio::main]
async fn main() {
    let handle = tokio::spawn(async {
        // Do some work in the background
        sleep(Duration::from_secs(1)).await;
        "done"
    });

    // Do other work concurrently
    println!("Processing...");

    let result = handle.await.unwrap();
    println!("Background task finished with result: {}", result);
}
```

- **Channels**: Use channels (like `tokio::sync::mpsc`) for safe communication between asynchronous tasks.
