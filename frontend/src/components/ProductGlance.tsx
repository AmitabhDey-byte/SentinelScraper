import { AnimatePresence, motion } from "framer-motion";
import type { Product } from "../types";
import { Sparkline } from "./Sparkline";
import { StockPill } from "./DashboardCards";

const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

export function ProductGlance({
  product,
  favorite,
  onClose,
  onFavorite,
}: {
  product: Product | null;
  favorite: boolean;
  onClose: () => void;
  onFavorite: (product: Product) => void;
}) {
  return (
    <AnimatePresence>
      {product && (
        <motion.div
          className="glance-backdrop"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onMouseDown={onClose}
        >
          <motion.aside
            className="product-glance"
            role="dialog"
            aria-modal="true"
            aria-label={`${product.name} at a glance`}
            initial={{ opacity: 0, y: 22, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.98 }}
            transition={{ type: "spring", stiffness: 360, damping: 28 }}
            onMouseDown={(event) => event.stopPropagation()}
          >
            <button className="glance-close" type="button" onClick={onClose} aria-label="Close product details">×</button>
            <div className="glance-media">
              {product.image_url ? <img src={product.image_url} alt="" /> : <span>▦</span>}
            </div>
            <div className="glance-copy">
              <p className="eyebrow">{product.site_name} / OBSERVED LISTING</p>
              <h2>{product.name}</h2>
              <div className="glance-price-row">
                <strong>{product.price === null ? "Price pending" : money.format(product.price)}</strong>
                <StockPill value={product.stock_status} />
              </div>
              <div className="glance-trend">
                <span>Observed price trace</span>
                <Sparkline values={product.price_history.map((point) => point.price)} />
              </div>
              <div className="glance-actions">
                <a href={product.listing_url} target="_blank" rel="noreferrer">Open listing ⤢</a>
                <button type="button" onClick={() => onFavorite(product)}>{favorite ? "Saved ♧" : "Save ♧"}</button>
                <button
                  type="button"
                  onClick={() => void navigator.clipboard?.writeText(product.listing_url)}
                >
                  Share ⧉
                </button>
              </div>
            </div>
          </motion.aside>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
