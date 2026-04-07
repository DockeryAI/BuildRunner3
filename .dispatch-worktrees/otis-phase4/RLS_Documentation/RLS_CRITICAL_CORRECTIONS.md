# CRITICAL RLS CORRECTIONS & CLARIFICATIONS

## ⚠️ IMPORTANT: Correct PostgreSQL RLS Syntax

### Corrected Policy Requirements by Operation Type

The RLS guides have been updated with the **CORRECT** PostgreSQL syntax:

| Operation | Required Clauses | Notes |
|-----------|-----------------|-------|
| **SELECT** | `USING` only | Controls which rows can be read |
| **INSERT** | `WITH CHECK` only | Controls which rows can be inserted |
| **UPDATE** | Both `USING` and `WITH CHECK` | USING: which rows can be updated<br>WITH CHECK: validation of new values |
| **DELETE** | `USING` only | Controls which rows can be deleted |

### ❌ INCORRECT Information (Previously in guides)
- **WRONG**: "INSERT needs both USING and WITH CHECK"
- **WRONG**: "All operations need both clauses"

### ✅ CORRECT Implementation

```sql
-- SELECT Policy (read operations)
CREATE POLICY "select_policy" ON table_name
FOR SELECT
USING (condition);  -- Only USING clause

-- INSERT Policy (create operations)
CREATE POLICY "insert_policy" ON table_name
FOR INSERT
WITH CHECK (condition);  -- Only WITH CHECK clause

-- UPDATE Policy (modify operations)
CREATE POLICY "update_policy" ON table_name
FOR UPDATE
USING (old_row_condition)      -- Which rows can be updated
WITH CHECK (new_row_condition); -- Validation of new values

-- DELETE Policy (remove operations)
CREATE POLICY "delete_policy" ON table_name
FOR DELETE
USING (condition);  -- Only USING clause
```

## 🔄 Supabase INSERT with .select() Pattern

For Supabase operations that insert and return data:

```javascript
const { data, error } = await supabase
  .from('table')
  .insert({ ... })
  .select();  // Returns the inserted row
```

You need **TWO policies**:
1. **INSERT policy** with `WITH CHECK` - allows the insert
2. **SELECT policy** with `USING` - allows reading the returned data

## 🛠️ Recent Fixes Applied

1. **location_detection_cache** - Now has proper RLS policies with correct PostgreSQL syntax
2. **Dashboard tables** - All have permissive policies for development
3. **Permission grants** - Re-applied in case they were wiped
4. **PostgREST cache** - Forced to reload

## ⚠️ Development vs Production

### Current Development Setup (TEMPORARY)
```sql
-- Permissive policies for development
CREATE POLICY "policy_name" ON table_name
FOR ALL
TO public
USING (true)
WITH CHECK (true);
```

### Production Requirements
- Replace `TO public` with proper user authentication
- Implement role-based access control (RBAC)
- Add tenant isolation for multi-tenant SaaS
- Use JWT claims for user identification
- Never use `USING (true)` in production

## 📚 References

This correction applies to:
- PostgreSQL 14+ RLS documentation
- Supabase RLS implementation
- PostgREST API requirements

Last Updated: 2024-11-22
