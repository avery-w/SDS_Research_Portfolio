function App() {
  return (
    <main className="page-shell">
      <section className="hero">
        <span className="tag">New standalone app</span>
        <h1>Built completely outside GPT-5 mini_prompt2</h1>
        <p>
          This project lives in its own folder and does not modify anything inside the
          existing prompt workspace.
        </p>
        <div className="cta-row">
          <button>Get started</button>
          <button className="secondary">View demo</button>
        </div>
      </section>

      <section className="grid">
        <article className="card">
          <h2>Independent</h2>
          <p>Separate folder, separate dependencies, and its own runtime.</p>
        </article>
        <article className="card">
          <h2>Safe</h2>
          <p>No edits were made to the files in GPT-5 mini_prompt2.</p>
        </article>
        <article className="card">
          <h2>Ready</h2>
          <p>You can run this project on its own and expand it freely.</p>
        </article>
      </section>
    </main>
  );
}

export default App;
