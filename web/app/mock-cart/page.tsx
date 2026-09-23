export default function MockCartPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 px-4">
      <section className="w-full max-w-lg rounded-3xl bg-white p-8 text-center shadow-soft">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-50 text-2xl text-emerald-600">✓</div>
        <h1 className="mt-5 text-2xl font-bold text-ink">Mock-корзина</h1>
        <p className="mt-3 text-sm leading-6 text-slate-500">Это демонстрационная страница. Реальный Cart API ekt.kz пока требует подтверждения владельца интеграции.</p>
        <a className="mt-6 inline-flex rounded-xl bg-ink px-5 py-3 text-sm font-semibold text-white" href="/">
          Вернуться в EKT AI
        </a>
      </section>
    </main>
  );
}
