# Phase 5 Plan: Dashboard — Deals Tab

## Tasks

1. **Add Deals types to types/index.ts** — DealItem, Hunt, PriceHistoryPoint, DealFilters
2. **Add Deals API methods to api.ts** — getDealItems, getHunts, createHunt, archiveHunt, getPriceHistory, dismissDeal, markDealRead
3. **Create DealsTab.tsx** — Hunt management panel + deal feed + price history chart + alert badge callback
4. **Create DealsTab.css** — Dark-friendly styling matching Intelligence tab aesthetic
5. **Update Dashboard.tsx** — Add 5th "Deals" tab with alert badge, wire DealsTab component

## Tests

- Unit test for DealsTab component rendering with mock data
- Verify types compile correctly (TypeScript check)
