## Order-list & order-detail patterns (verified on 订单 pages)
- **Countdown timer**: pending-ship rows carry `<span class="odl" data-sec="…">`; one global `setInterval(tickOrders,1000)` decrements and reformats HH:MM:SS; <1h turns red, 0 → "已超时,请尽快发货". Use a GLOBAL selector `document.querySelectorAll('.odl')` so list AND detail pages tick in sync (detail page embeds the same order's timer)
- **Data-loop design**: the 发货时限 (ship-by limit) set in the product publish form (step 4) is the SOURCE of the order countdown — keep demo data self-consistent across pages
- **Order detail timeline**: 5-node status timeline (下单→支付→待发货→发货→签收) with `.tl-item.done` (filled dot) / `.cur` (ring dot) / pending; separate logistics-trace timeline (揽收→干线→清关→派送→签收) lives INSIDE the 物流信息 card, collapsed while unshipped with a 查看物流轨迹 toggle
- **Buyer note (留言)**: order rows show a small gray `note-tag` (有留言) linking to detail; detail shows a quoted `.msg-line` block + time. This closes the "missing buyer-message indicator" gap vs TikTok Shop
- Tabs with counts: `.cnt.hot` red pill for the actionable tab (待发货)

