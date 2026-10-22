# Chef App — Backend v2 (fixed)
# مغز سیستم سفارش: نسخه درست‌شده با تراکنش اتمی
#
# مشکل نسخه قبلی: بررسی ظرفیت، ثبت سفارش و کم کردن ظرفیت ۳ تا
# عملیات جدا بودن. اگه ۲ نفر همزمان آخرین پرس رو سفارش بدن،
# هر دو قبول می‌شن (oversell). این نسخه همه‌اش رو توی یه
# تراکنش دیتابیس انجام می‌ده — غیرممکنه ظرفیت منفی بشه.

# ============================================================
# قدم ۱: این تابع رو توی Supabase SQL Editor اجرا کن
# (Dashboard → SQL Editor → New query → Run)
# ============================================================

SQL_FUNCTION = """
create or replace function place_order(
  p_user_id text,
  p_schedule_id uuid,
  p_delivery_type text
)
returns jsonb
language plpgsql
as $$
declare
  v_max int;
  v_sold int;
  v_left int;
begin
  -- قفل ردیف: هیچ سفارش دیگه‌ای همزمان نمی‌تونه این رو بخونه
  select max_capacity, sold_count
    into v_max, v_sold
    from "DailySchedules"
   where id = p_schedule_id
   for update;

  if not found then
    return jsonb_build_object(
      'status', 'error',
      'message', 'این منو در تاریخ مورد نظر یافت نشد.'
    );
  end if;

  if v_sold >= v_max then
    return jsonb_build_object(
      'status', 'failed',
      'message', 'متاسفیم! ظرفیت این غذا برای این روز کاملاً پر شده است (Sold Out).'
    );
  end if;

  insert into "Orders"(user_id, schedule_id, delivery_type, status, created_at)
  values (p_user_id, p_schedule_id, p_delivery_type,
          'Pending Kitchen Approval', now());

  update "DailySchedules"
     set sold_count = v_sold + 1
   where id = p_schedule_id;

  v_left := v_max - v_sold - 1;

  return jsonb_build_object(
    'status', 'success',
    'message', 'سفارش شما با موفقیت ثبت شد!',
    'portions_left', v_left
  );
end;
$$;
"""

# ============================================================
# قدم ۲: کد پایتون — حالا فقط یه خط صدا می‌زنه
# ============================================================
# پیش‌نیاز: pip install supabase

import os
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://your-project.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "your-anon-key")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def check_capacity_and_order(user_id, schedule_id, delivery_type):
    """
    مغز سیستم v2: همه‌چیز توی یه تراکنش اتمی.
    delivery_type: 'Pickup' یا 'Delivery'
    """
    try:
        resp = supabase.rpc("place_order", {
            "p_user_id": user_id,
            "p_schedule_id": schedule_id,
            "p_delivery_type": delivery_type,
        }).execute()
        result = resp.data or {}
        if result.get("status") == "success":
            print(f"✅ سفارش ثبت شد! {result.get('portions_left')} پرس مانده.")
        else:
            print(f"⚠️ {result.get('message')}")
        return result
    except Exception as e:
        print(f"❌ خطای سیستمی: {e}")
        return {"status": "error", "message": "خطا در برقراری ارتباط با سرور."}


if __name__ == "__main__":
    print("--- SQL function (run once in Supabase SQL Editor) ---")
    print(SQL_FUNCTION)
    print("--- test call ---")
    print(check_capacity_and_order(
        user_id="U-123", schedule_id="SCH-1", delivery_type="Delivery"))
