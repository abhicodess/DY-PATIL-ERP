from utils.pg_wrapper import exe

def add_otp_template():
    sql = "INSERT INTO sms_templates (slug, body) VALUES ('otp_msg', 'Your ERP verification code is {{otp}}. Valid for 10 minutes.') ON CONFLICT (slug) DO UPDATE SET body = EXCLUDED.body"
    exe(sql)
    print("OTP Template added/updated.")

if __name__ == "__main__":
    add_otp_template()
