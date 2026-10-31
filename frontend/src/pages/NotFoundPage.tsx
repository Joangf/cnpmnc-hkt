import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <section className="mx-auto max-w-xl border-3 border-ink">
      <div className="border-b-3 border-ink bg-blush p-6 sm:p-8">
        <p className="text-display font-extrabold" aria-hidden="true">
          404
        </p>
      </div>
      <div className="space-y-5 p-6 sm:p-8">
        <h1 className="page-title">Page not found</h1>
        <p>The page may have moved. Start again from the homepage.</p>
        <Link className="btn-primary" to="/">
          Go home
        </Link>
      </div>
    </section>
  )
}
