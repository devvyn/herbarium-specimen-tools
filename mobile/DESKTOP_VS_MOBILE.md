# Desktop vs Mobile Review Interfaces

**Quick Reference:** Understanding the two review interfaces in this project.

## TL;DR

| | Desktop | Mobile |
|---|---------|--------|
| **File** | `src/review/web_app.py` | `mobile/` + `src/review/mobile_api.py` |
| **Status** | ✅ In main branch | 🆕 This PR |
| **Run** | `python -m src.review.web_app --port 5002` | `python mobile/run_mobile_server.py --dev` |
| **Platform** | Desktop browser | iPhone Safari |
| **Auth** | None | JWT required |
| **Best for** | Workstation curation | Field/mobile review |

## Why Two Interfaces?

They solve **different problems:**

**Desktop = Detailed workstation curation**
- Large screen
- Keyboard/mouse
- Trusted network
- Batch processing

**Mobile = Quick field review**
- iPhone/mobile
- Touch gestures
- Internet access
- On-the-go decisions

## Can They Coexist?

**Yes!** They're completely independent:

✅ Different directories (no file conflicts)
✅ Different ports (can run simultaneously)
✅ Share core logic (`engine.py`, `validators.py`)
✅ Independent deployment

## Quick Decision Tree

```
Need to review specimens?
│
├─ On iPhone? → Use MOBILE interface
├─ At desk with keyboard? → Use DESKTOP interface
├─ Over internet? → Use MOBILE (has auth/security)
├─ On trusted network? → Either works
└─ Want serverless? → Use MOBILE (AWS Lambda)
```

## Architecture Comparison

**Desktop Interface:**
```
Browser → Quart (Python) → ReviewEngine → Data
```

**Mobile Interface:**
```
iPhone Safari → FastAPI (Python) → ReviewEngine → Data
                ↓
        Optional: AWS Lambda (serverless)
```

Both use the **same ReviewEngine** for consistency!

## Security Note

**Desktop:** No authentication (assumes trusted network)
**Mobile:** Full enterprise security (JWT, bcrypt, rate limiting, CORS)

**If deploying over internet, use mobile interface.**

## Complete Documentation

See: [`docs/review-interfaces.md`](../docs/review-interfaces.md)

## Questions?

- Desktop docs: Main `README.md`
- Mobile docs: `mobile/README.md`, `mobile/SECURITY.md`
- Deployment: `mobile/AWS_DEPLOYMENT.md`
