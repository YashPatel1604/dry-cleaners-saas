const ORDER_SKU_PREFIX = "ORD";
const ORDER_SKU_PADDING = 8;
const MAX_TAG_COPIES = 20;

export type OrderTagLabelSize = "2x1" | "4x2";

const LABEL_DIMENSIONS: Record<OrderTagLabelSize, { widthIn: number; heightIn: number }> = {
  "2x1": { widthIn: 2, heightIn: 1 },
  "4x2": { widthIn: 4, heightIn: 2 },
};

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function formatOrderSku(orderId: number | string): string {
  const parsedId = Number(orderId);
  if (Number.isInteger(parsedId) && parsedId > 0) {
    return `${ORDER_SKU_PREFIX}-${String(parsedId).padStart(ORDER_SKU_PADDING, "0")}`;
  }
  return `${ORDER_SKU_PREFIX}-${String(orderId)}`;
}

export function orderBarcodePath(orderId: number | string): string {
  return `/api/orders/${orderId}/barcode.svg/`;
}

export function openOrderSkuTagPrint(options: {
  orderId: number | string;
  orderSku?: string;
  customerName?: string;
  labelSize?: OrderTagLabelSize;
  copies?: number;
  barcodeDataUri?: string;
  openedWindow?: Window | null;
}): boolean {
  const { orderId, customerName } = options;
  const orderSku = options.orderSku || formatOrderSku(orderId);
  const barcodePath = orderBarcodePath(orderId);
  const labelSize: OrderTagLabelSize =
    options.labelSize && options.labelSize in LABEL_DIMENSIONS
      ? options.labelSize
      : "2x1";
  const copies = Math.max(1, Math.min(MAX_TAG_COPIES, Math.trunc(options.copies ?? 1)));
  const dimensions = LABEL_DIMENSIONS[labelSize];
  const printWindow =
    options.openedWindow ??
    window.open("", "_blank", "width=480,height=640");

  if (!printWindow) return false;

  const safeSku = escapeHtml(orderSku);
  const safeOrderNumber = escapeHtml(String(orderId));
  const safeCustomerName = customerName ? escapeHtml(customerName) : "";
  const barcodeSrc = options.barcodeDataUri || barcodePath;
  const labelBlocks = Array.from({ length: copies })
    .map((_, index) => {
      const breakClass = index < copies - 1 ? " tag-break" : "";
      return `<main class="tag${breakClass}">
      <p class="kicker">Order Tag</p>
      <h1 class="sku">${safeSku}</h1>
      <div class="meta">
        <div>Order #: ${safeOrderNumber}</div>
        ${safeCustomerName ? `<div>Customer: ${safeCustomerName}</div>` : ""}
      </div>
      <div class="barcode">
        <img class="order-barcode" src="${barcodeSrc}" alt="Barcode ${safeSku}" />
      </div>
    </main>`;
    })
    .join("");

  printWindow.document.write(`<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Order Tag ${safeSku}</title>
    <style>
      @page { size: ${dimensions.widthIn}in ${dimensions.heightIn}in; margin: 0; }
      body {
        margin: 0;
        padding: 16px;
        font-family: Arial, sans-serif;
        color: #111827;
        background: #f3f4f6;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 12px;
      }
      .tag {
        box-sizing: border-box;
        width: ${dimensions.widthIn}in;
        height: ${dimensions.heightIn}in;
        padding: ${labelSize === "2x1" ? "0.08in" : "0.16in"};
        background: #fff;
        border: 1px solid #d1d5db;
        border-radius: 8px;
      }
      .tag-break { page-break-after: always; }
      .kicker {
        margin: 0;
        font-size: ${labelSize === "2x1" ? "8px" : "10px"};
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }
      .sku {
        margin: 2px 0 0;
        font-size: ${labelSize === "2x1" ? "15px" : "24px"};
        font-weight: 700;
        letter-spacing: 0.04em;
      }
      .meta {
        margin-top: ${labelSize === "2x1" ? "2px" : "8px"};
        font-size: ${labelSize === "2x1" ? "9px" : "13px"};
        color: #374151;
        line-height: 1.2;
      }
      .barcode {
        margin-top: ${labelSize === "2x1" ? "4px" : "12px"};
        text-align: center;
      }
      .barcode img {
        width: 100%;
        height: ${labelSize === "2x1" ? "0.35in" : "0.8in"};
        object-fit: contain;
      }
      @media print {
        html, body {
          width: ${dimensions.widthIn}in;
          min-height: ${dimensions.heightIn}in;
          margin: 0;
          padding: 0;
          background: #fff;
          display: block;
        }
        .tag {
          border: none;
          border-radius: 0;
        }
      }
    </style>
  </head>
  <body>
    ${labelBlocks}
    <script>
      (function () {
        let printed = false;
        const triggerPrint = function () {
          if (printed) return;
          printed = true;
          setTimeout(function () { window.print(); }, 200);
        };
        const barcodes = Array.from(document.querySelectorAll(".order-barcode"));
        if (!barcodes.length) {
          triggerPrint();
          return;
        }
        let pending = 0;
        barcodes.forEach(function (barcode) {
          if (barcode.complete) return;
          pending += 1;
          const done = function () {
            pending -= 1;
            if (pending <= 0) triggerPrint();
          };
          barcode.addEventListener("load", done, { once: true });
          barcode.addEventListener("error", done, { once: true });
        });
        if (pending <= 0) {
          triggerPrint();
          return;
        }
        setTimeout(triggerPrint, 1500);
      })();
    </script>
  </body>
</html>`);
  printWindow.document.close();

  return true;
}
