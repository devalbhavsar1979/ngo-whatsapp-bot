# Meta WhatsApp Cloud API Setup

This guide connects the NGO WhatsApp bot to Meta's WhatsApp Cloud API. Deploy
the app to Vercel first so Meta can reach its public HTTPS webhook.

> Meta occasionally changes dashboard labels and navigation. If a label differs,
> use the WhatsApp **API Setup** and **Configuration** panels in your app
> dashboard.

## What you need

- A Meta account registered for Meta for Developers.
- A Meta developer app with the WhatsApp use case.
- A WhatsApp Business Account (WABA).
- A Vercel deployment URL and access to its environment-variable settings.
- A phone that can receive an SMS or voice call for verification when adding a
  real business phone number.

For initial testing, Meta provides a test number. You can connect that first
without registering your organization's number.

## 1. Create a Meta developer app

1. Open [Meta for Developers](https://developers.facebook.com/) and sign in.
2. Complete developer registration if prompted.
3. Open [My Apps](https://developers.facebook.com/apps/) and choose **Create
   App**.
4. Choose the **Connect with customers through WhatsApp** use case (or the
   closest WhatsApp/business-messaging option shown).
5. Select the business portfolio to associate with the app, or create one.
6. Review the details and create the app.
7. In the app dashboard, open the WhatsApp use case/product and select **API
   Setup** or **Start using the API**.
8. Select or create the WABA to use with the bot.

Keep the app in development mode while testing. Do not share the app with
unapproved users or publish it until you have completed Meta's requirements for
your business and use case.

## 2. Try the test number

In the app's **WhatsApp → API Setup** panel:

1. Select the Meta-provided test **From** number.
2. In the **To** recipient selector, choose **Add recipient** (or **Manage
   phone number list**, if that is the label shown).
3. Enter the WhatsApp number you will use to test the bot, including its
   country code (for example, `14155550123`). This is your personal/test
   recipient number, not the Meta test **From** number.
4. Complete Meta's verification for that recipient. Meta may send a
   verification code by SMS or WhatsApp; enter it in the dashboard.
5. Confirm the recipient appears as a selectable **To** number in API Setup.
   Repeat these steps for each person who needs to test. Meta limits the
   number of recipients for a test setup.
6. Generate a temporary access token for setup testing.
7. Use Meta's **Send message** control to send its sample message to your
   recipient. This checks that the test number and recipient are configured.
8. Record the **Phone Number ID** shown for the selected From number. This is
   the value needed by the bot; it is not the visible phone number or the WABA
   ID.

Temporary tokens expire. They are useful for an initial check, but should not
be relied on for an unattended deployment.

After you have connected the webhook, send a WhatsApp message from the
verified recipient phone to the Meta test **From** number. The recipient
allowlist authorizes test interaction with the Cloud API; it does not add a
phone number for the bot to send from.

## 3. Add a real business phone number (when ready)

You can keep using the test number while developing. For a real deployment:

1. In **WhatsApp → API Setup** or WhatsApp Manager, choose **Add phone
   number** and follow Meta's business/profile prompts.
2. Use a number your organization owns and can verify by SMS or voice call.
   Follow Meta's instructions if the number is already registered with
   WhatsApp; do not remove or migrate an existing number until you understand
   the effect on its current WhatsApp service.
3. Complete the verification and registration steps Meta shows, then confirm
   the number's status is connected/active.
4. Select that number in the API Setup panel and copy its **Phone Number ID**.
   Use the ID for the number the bot will send messages from.
5. Complete any business verification, display-name review, payment, or
   messaging-limit requirements Meta presents for your account.

Menu labels and eligibility checks can vary by account and country. Follow the
requirements shown in your Meta dashboard.

## 4. Create a durable access token

The temporary token from API Setup can expire. Before unattended operation,
create a system-user token in Meta Business Settings:

1. Open the business portfolio associated with the app.
2. In **Business Settings**, create or select a system user.
3. Assign that system user the WhatsApp assets it needs: the app and the
   correct WABA/phone number, with permissions to manage the integration.
4. Generate a token for the app and select the WhatsApp permissions Meta
   requires. The bot sends messages and retrieves uploaded media; commonly
   relevant permissions include `whatsapp_business_messaging` and
   `whatsapp_business_management`.
5. Choose the longest appropriate token duration available to your account.
   Record its expiry and establish a rotation reminder.

Meta may require business verification or additional app access before a
system-user token can be used in production. Follow the permissions and review
requirements shown in your dashboard. Treat the token like a password.

## 5. Add Meta credentials to Vercel

In the Vercel project, open **Settings → Environment Variables** and configure:

| Environment variable | Meta value |
|---|---|
| `PHONE_NUMBER_ID` | The Phone Number ID for the selected sending number |
| `ACCESS_TOKEN` | The access token for the app/WABA/number |
| `VERIFY_TOKEN` | A private string you invent; it is not issued by Meta |

Add these values to the **Production** environment. Add them to Preview only
when intentionally testing a Preview deployment. Save and redeploy after
changing environment variables.

Create a strong verify token, for example with a password manager. It can be
letters, digits, and punctuation; make sure the same exact string is used in
Vercel and the Meta callback form. Do not put the Meta access token in the
verify-token field.

Do not paste tokens into source code, commit them, or include them in support
screenshots or logs.

## 6. Configure the webhook callback

First confirm that the Vercel production deployment is live and that
`https://<your-project>.vercel.app/health` responds successfully.

In the Meta app dashboard:

1. Open **WhatsApp → Configuration** (or **Use cases → Customize →
   Configuration**, depending on how the app was created).
2. Find **Webhook** and choose **Edit** or **Configure**.
3. Enter the Vercel production callback URL:

   ```text
   https://<your-project>.vercel.app/webhook
   ```

4. Enter the exact private string stored as `VERIFY_TOKEN` in Vercel.
5. Choose **Verify and Save**.

The app's `GET /webhook` endpoint implements Meta's verification challenge.
Once verified, Meta sends events to `POST /webhook`.

## 7. Subscribe to WhatsApp events

In the same Meta **Configuration** panel:

1. Find **Webhook fields**.
2. Subscribe the app to the **messages** field. This is required for incoming
   user messages and includes delivery/read status notifications.
3. If Meta presents a WABA/account subscription step, subscribe the correct
   WhatsApp Business Account to this app as well.
4. Save the changes.

This app handles incoming text, interactive replies, images, and documents. It
uses outgoing message status events to sequence the greeting image and language
picker. It does not need unrelated webhook fields for the current flow.

## 8. Test the full integration

1. Make sure `PHONE_NUMBER_ID`, `ACCESS_TOKEN`, and `VERIFY_TOKEN` are set in
   Vercel and the latest deployment has completed.
2. Send `hi` from a verified test recipient to the connected WhatsApp number.
3. Confirm the greeting image and language-selection list arrive.
4. Choose a language and try a category/FAQ interaction.
5. Check Vercel function logs for webhook activity and Meta API errors.
6. After successful testing, complete any Meta business/app review steps
   required to serve real customers.

The image greeting also requires
`https://<your-project>.vercel.app/static/cerc_logo.png` to be publicly
accessible.

## Troubleshooting

### I sent “Hi” but got no bot response

Follow these checks in order. The first message from a new chat should trigger
the CERC greeting image and then a language-selection list.

1. **Check the direction of the test.** Send `Hi` from your verified personal
   WhatsApp recipient **to the Meta test From number**. Do not send `Hi` from
   the Meta test number to your personal phone. In API Setup, the test number
   is the bot's sender; your verified phone is the recipient/user.
2. **Check the message window in WhatsApp.** Open the conversation with the
   Meta test number and make sure your `Hi` appears as an outgoing message.
   The "Send message" button in API Setup only sends Meta's sample message; it
   does not itself test the bot's incoming-message flow.
3. **Check the public deployment.** Open these URLs in a private/incognito
   browser window:
   - `https://<your-project>.vercel.app/health` should return healthy JSON.
   - `https://<your-project>.vercel.app/static/cerc_logo.png` should show the
     logo.
   Make sure Meta is configured with the production domain and the Vercel
   deployment is public, not behind Vercel Deployment Protection/login.
4. **Check that Meta is delivering the webhook.** In Meta's app dashboard,
   open **WhatsApp → Configuration → Webhook** and confirm the callback URL
   ends exactly with `/webhook`, the webhook is verified, and the app is
   subscribed to **messages**. If the dashboard offers webhook delivery or
   event logs, inspect the delivery for your test `Hi`.
5. **Check Vercel function logs.** In Vercel, open the project and inspect
   **Logs** for a `POST /webhook` at the time you sent `Hi`.
   - **No `POST /webhook`:** Meta did not reach this deployment. Recheck
     webhook verification, the **messages** subscription, correct WABA, and
     that you sent to the test From number from an allowed recipient.
   - **A POST with a non-2xx response or a function error:** open its details
     for the traceback. Check the latest deployment and its runtime logs.
   - **A POST returns 200 but there is no WhatsApp reply:** the app accepted
     the webhook, so inspect the same logs for `Error sending image`,
     `Error sending interactive list`, or Meta API response details. Confirm
     `PHONE_NUMBER_ID` is the Phone Number ID for the bot's selected From
     number, and `ACCESS_TOKEN` is valid for that number and has
     `whatsapp_business_messaging`. Redeploy after correcting environment
     variables.
6. **Check Vercel Production environment variables.** Confirm `PHONE_NUMBER_ID`,
   `ACCESS_TOKEN`, and `VERIFY_TOKEN` exist under the **Production** scope.
   The verify token must exactly match Meta's value. Never share the access
   token in screenshots or messages.
7. **Try the test recipient again.** The personal phone sending the message
   must be added and verified in the test-number recipient list. Confirm the
   test number is still selected as the bot's **From** number.

When asking for help, share only the HTTP status/error text and relevant
redacted logs. Do not post access tokens, verify tokens, service-account JSON,
or personal phone numbers.

### Meta error `(#131030) Recipient phone number not in allowed list`

This error means the app received the incoming WhatsApp message and tried to
reply, but Meta's **test sender number** is not allowed to message the
recipient yet. It is an allowlist issue, not a webhook delivery issue.

1. In Vercel logs, find the `From:` phone number on the incoming message. This
   is the user's/recipient's number the bot is attempting to reply to.
2. In Meta, open the app's **WhatsApp → API Setup** panel.
3. In the **To** recipient selector, add that user's number as a test recipient
   and complete Meta's verification. The number must be the same WhatsApp
   account you sent `Hi` from, with the correct country code.
4. Confirm the number appears in the allowed **To** recipient list. Keep the
   Meta test number selected as the bot's **From** number.
5. Send a new `Hi` from that verified user account to the Meta test number and
   check the Vercel logs again.

For example, if the log says `Recipient phone number not in allowed list:
16315550123`, add that destination number (your actual test number) in API
Setup. Do not copy the example number.

Meta may still reject other recipients while using its test number. To message
people who are not in the test allowlist, configure an eligible, registered
business phone number for the Cloud API and meet Meta's production requirements.

### Meta error `(#131005) Access denied`

This is different from `(#131030) Recipient phone number not in allowed list`.
If it appears in Vercel immediately after the app logs an incoming message, the
webhook reached the app but Meta denied an outgoing WhatsApp API request.
Check:

1. `PHONE_NUMBER_ID` in Vercel is the **Phone Number ID** for the selected bot
   sender—not the visible phone number, WABA ID, or a stale test number.
2. `ACCESS_TOKEN` belongs to the same Meta app/business and is authorized for
   the WABA and phone number above. If you use a system-user token, assign that
   system user the correct WhatsApp assets.
3. The token has the `whatsapp_business_messaging` permission. If the bot is
   downloading attachments, it also needs appropriate WhatsApp Business
   permissions for media access.
4. The token is active and was added to the Vercel **Production** environment.
   After changing it, redeploy the Vercel project.
5. In **WhatsApp → API Setup**, try Meta's own **Send message** control to the
   same verified test recipient. If Meta's own send also fails with access
   denied, resolve the token/asset permission in Meta before troubleshooting
   the Flask webhook.

Do not post the access token. To narrow this down, retain the API response's
`error_data.details`, the app log line immediately before `Response details`,
and whether the failure came from Meta's API Setup or Vercel. Redact phone
numbers and credentials before sharing.

| Symptom | Check |
|---|---|
| **`GET /webhook` returns 403** | The app was reached, but Meta's verification request did not match. Confirm `VERIFY_TOKEN` is set in the Vercel **Production** environment, redeploy after adding/changing it, then enter the exact same value in Meta's webhook **Verify token** field. Do not use `ACCESS_TOKEN` here. Check for extra spaces or quotation marks; never share either token in logs or screenshots. |
| **Verify and Save** fails for another reason | The callback must include `/webhook`; confirm the Vercel deployment responds and inspect the Vercel function logs. |
| Webhook verifies but no incoming messages arrive | Subscribe the app to the **messages** field and the correct WABA; confirm the sender number is connected and your WhatsApp number was added and verified as a test recipient in API Setup. |
| Bot receives messages but cannot reply | Check `PHONE_NUMBER_ID` belongs to the selected sending number and `ACCESS_TOKEN` is valid for that app/WABA and has the required permissions. |
| Messages stop working after a while | Check whether the access token expired or was revoked; rotate it in Meta and update Vercel. |
| Greeting image is missing | Open `/static/cerc_logo.png` directly over HTTPS and confirm the public file is deployed. |
| Meta dashboard says the app or business needs review | Complete the verification, access, and policy requirements displayed in Meta Business Settings/App Dashboard. |

## Official Meta references

- [WhatsApp Cloud API: Get Started](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started)
- [WhatsApp Cloud API webhooks](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks)
- [WhatsApp business phone numbers](https://developers.facebook.com/docs/whatsapp/cloud-api/phone-numbers)
