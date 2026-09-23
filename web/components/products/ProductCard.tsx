import type { ChatProduct } from "@/lib/types";

interface ProductCardProps {
  product: ChatProduct;
}

export function ProductCard({ product }: ProductCardProps) {
  return (
    <article className="min-w-0 max-w-full overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      <div className="relative flex h-36 items-center justify-center overflow-hidden bg-slate-100 sm:h-40">
        {product.image_url ? (
          <img className="h-full w-full object-cover" src={product.image_url} alt={product.name} />
        ) : (
          <div className="flex flex-col items-center gap-2 text-slate-400" aria-label="Изображение недоступно">
            <span className="text-3xl">▧</span>
            <span className="text-xs">Нет изображения</span>
          </div>
        )}
        <span className="absolute left-3 top-3 rounded-full bg-white/90 px-2.5 py-1 text-[11px] font-semibold text-slate-600 shadow-sm">
          В наличии
        </span>
      </div>
      <div className="space-y-3 p-4">
        <div>
          <p className="line-clamp-2 min-h-10 text-sm font-semibold leading-5 text-ink">{product.name}</p>
          <p className="mt-1 text-xs text-slate-500">Артикул: {product.article}</p>
        </div>
        <div className="flex min-w-0 flex-wrap items-end justify-between gap-3">
          <div>
            <p className="break-words text-lg font-bold text-ink">
              {new Intl.NumberFormat("ru-RU").format(product.price.amount)} {product.price.currency}
            </p>
            <p className="text-xs text-emerald-600">Остаток: {product.availability.quantity_total} шт.</p>
          </div>
          <a
            className="shrink-0 rounded-xl bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-200"
            href={product.product_url}
            target="_blank"
            rel="noreferrer"
          >
            Подробнее
          </a>
        </div>
      </div>
    </article>
  );
}
