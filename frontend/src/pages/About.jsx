export default function About() {
  return (
    <article className="mx-auto max-w-2xl space-y-5 text-stone-700">
      <h1 className="text-2xl font-extrabold text-stone-900">About PastQ</h1>

      <section className="card space-y-2 p-5 text-sm leading-relaxed">
        <h2 className="font-semibold text-stone-900">How it works</h2>
        <p>
          Students upload photos or PDFs of past exam and test papers. An AI model reads each paper into separate questions and tags the topic
          each one tests. The uploader can check and correct everything.
        </p>
        <p>
          Anyone signed in can ask for a step-by-step explanation of a question. It's generated once, then shared with everyone, and you can
          rate whether it helped. Explanations are AI-written, so always check them against your lecture notes.
        </p>
        <p>
          Each course page shows the topics that appear most often across the years, so you know where to focus your revision.
        </p>
      </section>

      <section className="card space-y-2 p-5 text-sm leading-relaxed">
        <h2 className="font-semibold text-stone-900">What to share</h2>
        <p>
          Share past questions that students already circulate for revision. Please don't upload marking schemes, unreleased papers or
          anything confidential.
        </p>
      </section>

      <section className="card space-y-2 p-5 text-sm leading-relaxed">
        <h2 className="font-semibold text-stone-900">Takedowns and corrections</h2>
        <p>
          Every paper has a <strong>Report a problem</strong> link. Moderators review reports and can hide a paper straight away. If you're a
          lecturer or department and want a paper removed, report it with the reason and it will be taken down.
        </p>
      </section>
    </article>
  );
}
