import { createMockDropServer } from "./server.js";

const port = Number.parseInt(process.env.PORT ?? "8080", 10);
const host = process.env.HOST ?? "0.0.0.0";
const server = createMockDropServer();

server.listen(port, host, () => {
  console.log(`MockDrop listening on http://${host}:${port}`);
});

function shutdown(signal) {
  console.log(`MockDrop received ${signal}; closing server`);
  server.close((error) => {
    if (error) {
      console.error("MockDrop shutdown failed", error);
      process.exitCode = 1;
    }
  });
}

process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));
