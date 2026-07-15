# Week 4 -- Spaced Repetition Scheduler + Authentication: Build Plan

Goal: Add JWT authentication to protect all endpoints, implement the SM-2 spaced repetition algorithm so answered questions are scheduled for review, and build the frontend auth flow + due reviews UI.

---

## Overview

| Part | Focus | Dependencies | Est. Hours |

| 1 | Auth API: register, login, refresh | None | 3-4 hrs |
| 2 | Auth middleware + route protection | Part 1 | 2 hrs |
| 3 | Frontend auth flow: login, register, token storage | Parts 1-2 | 3-4 hrs |
| 4 | SM-2 algorithm (pure function) | None | 2-3 hrs |
| 5 | Attempt recording + schedule update endpoint | Part 4 | 2-3 hrs |
| 6 | Due reviews endpoint + review mode | Part 5 | 2-3 hrs |
| 7 | Background review checker worker | Part 6 | 1-2 hrs |
| 8 | Frontend: due reviews UI + dashboard integration | Parts 5-6 | 3-4 hrs |
| 9 | Testing: auth + SM-2 verification | All | 2-3 hrs |
| | **Total** | | **~20-26 hrs** |

---

## Part 1 -- Auth API: Register, Login, Refresh

### Endpoints

| Method | Path | Request | Response |

| POST | `/auth/register` | `UserRegister` (email, password) | `UserResponse` |
| POST | `/auth/login` | `UserLogin` (email, password) | `TokenResponse` |
| POST | `/auth/refresh` | `{ refresh_token: str }` | `TokenResponse` |
| POST | `/auth/logout` | header: `Authorization` | `{ message: "logged out" }` |

### Files to create

| File | Action |
| `backend/app/api/auth.py` | New -- all 4 auth endpoints |
| `backend/app/api/router.py` | Add auth router |

### Register flow

```
1. Validate email format (Pydantic EmailStr handles this)
2. Check if email already exists -> 409 Conflict
3. Hash password with bcrypt (passlib)
4. Create user row
5. Return UserResponse (id, email, created_at)
```

### Login flow

```
1. Look up user by email -> 401 if not found
2. Verify password hash -> 401 if mismatch
3. Generate access token (JWT, 30 min expiry)
4. Generate refresh token (JWT, 7 day expiry)
5. Create session row with jwt_id from access token
6. Return TokenResponse (access_token, refresh_token, token_type)
```

### Refresh flow

```
1. Decode refresh token -> 401 if expired/invalid
2. Verify token type == "refresh" -> 401 if not
3. Look up user -> 401 if not found
4. Revoke old session (delete by user_id)
5. Generate new access + refresh tokens
6. Create new session row
7. Return new TokenResponse
```

### Logout flow

```
1. Extract jwt_id from current access token
2. Delete session row matching that jwt_id
3. Return success message
```

### Done when
- Register with a new email succeeds, duplicate email returns 409
- Login with correct password returns two tokens
- Login with wrong password returns 401
- Refresh with a valid refresh token returns new tokens
- Logout invalidates the session

---

## Part 2 -- Auth Middleware + Route Protection

### Files to create/modify

| File | Action |
| `backend/app/core/deps.py` | New -- `get_current_user` dependency |
| `backend/app/api/documents.py` | Add `current_user` dependency to all routes |
| `backend/app/api/quiz.py` | Add `current_user` dependency to all routes |

### `get_current_user` dependency

```python
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(401)
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")

    user = await db.get(User, uuid.UUID(user_id))
    if not user:
        raise HTTPException(401, "User not found")

    # Optional: verify session still exists (for logout revocation)
    session = await db.execute(
        select(Session).where(Session.jwt_id == payload.get("jti"))
    )
    if not session.scalar_one_or_none():
        raise HTTPException(401, "Session revoked")

    return user
```

### OAuth2 scheme

```python
from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
```

### Routes to protect

| Route group | Protection |
| `/auth/register` | Public |
| `/auth/login` | Public |
| `/auth/refresh` | Public (token in body, not header) |
| `/auth/logout` | Authenticated |
| `/health` | Public |
| `/documents/*` | Authenticated -- filter by `current_user.id` |
| `/quiz/*` | Authenticated -- filter by `current_user.id` |
| All future routes | Authenticated by default |

### Data scoping
Once auth is in place, all document and quiz queries must filter by `user_id = current_user.id`. A user must never see another user's documents, questions, or attempts.

### Done when
- Hitting `/documents/upload` without a token returns 401
- Hitting `/documents/upload` with a valid token succeeds
- Hitting any protected route with an expired token returns 401
- After logout, the same token returns 401 (session revoked)

---

## Part 3 -- Frontend Auth Flow

### Files to create/modify

| File | Action |
| `frontend/src/hooks/useAuth.jsx` | New -- auth context provider |
| `frontend/src/components/ProtectedRoute.jsx` | New -- redirect to login if no token |
| `frontend/src/pages/LoginPage.jsx` | Add real API call on submit |
| `frontend/src/pages/RegisterPage.jsx` | Add real API call on submit |
| `frontend/src/App.jsx` | Wrap with AuthProvider, protect routes |
| `frontend/src/api/client.js` | Add refresh token interceptor |

### Auth context (useAuth)

```javascript
const AuthContext = createContext(null)

function AuthProvider({ children }) {
    const [user, setUser] = useState(null)
    const [loading, setLoading] = useState(true)

    // On mount: check if refresh token exists in localStorage
    // If yes: try to refresh -> set user
    // If no: set user = null

    const login = async (email, password) => { ... }
    const register = async (email, password) => { ... }
    const logout = async () => { ... }

    return (
        <AuthContext.Provider value={{ user, login, register, logout, loading }}>
            {children}
        </AuthContext.Provider>
    )
}
```

### Token storage strategy

| Token | Storage | Rationale |

| Access token | `sessionStorage` | Cleared on tab close, not accessible by other tabs |
| Refresh token | `localStorage` | Persists across sessions for seamless re-login |

### ProtectedRoute component

```javascript
function ProtectedRoute({ children }) {
    const { user, loading } = useAuth()
    if (loading) return <LoadingSpinner />
    if (!user) return <Navigate to="/login" replace />
    return children
}
```

### Login page updates
- On submit: call `POST /auth/login`
- On success: store tokens, redirect to `/dashboard`
- On error: show error message below the form

### Register page updates
- On submit: call `POST /auth/register`
- On success: redirect to `/login` with a success message
- On error: show error (duplicate email, weak password, etc.)

### Axios interceptor update
- On 401 response: attempt token refresh using stored refresh token
- If refresh succeeds: retry the original request with the new token
- If refresh fails: clear tokens, redirect to `/login`

### Done when
- Register creates a new account and redirects to login
- Login stores tokens and redirects to dashboard
- Refreshing the page while logged in stays logged in (refresh token works)
- Navigating to `/dashboard` while logged out redirects to `/login`
- Logout clears tokens and redirects to login

---

## Part 4 -- SM-2 Algorithm (Pure Function)

### Files to create

| File | Purpose |

| `backend/app/services/scheduler.py` | SM-2 core logic as a pure function |

### SM-2 algorithm

The SuperMemo 2 algorithm calculates when to next review a question based on how well you answered it.

### Inputs

| Param | Type | Description |

| `quality` | int (0-5) | How well the user answered. 0=blackout, 5=perfect |
| `repetitions` | int | Number of consecutive correct reviews |
| `ease_factor` | float | Multiplier for interval growth (starts at 2.5) |
| `interval` | int | Current interval in days |

### Simplified quality mapping

Since our quiz only gives correct/incorrect (not a 0-5 scale), map as follows:

| User result | Quality score | Reasoning |

| Incorrect | 1 | Poor recall |
| Correct but slow (> 30s) | 3 | Hesitant recall |
| Correct and fast (<= 30s) | 5 | Perfect recall |

### Implementation

```python
def sm2(quality: int, repetitions: int, ease_factor: float, interval: int) -> tuple[int, float, int]:
    """
    Returns (new_interval, new_ease_factor, new_repetitions)
    """
    if quality < 3:
        # Failed: reset
        new_repetitions = 0
        new_interval = 1
    else:
        # Passed
        new_repetitions = repetitions + 1
        if new_repetitions == 1:
            new_interval = 1
        elif new_repetitions == 2:
            new_interval = 6
        else:
            new_interval = round(interval * ease_factor)

    new_ease_factor = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ease_factor = max(1.3, new_ease_factor)  # floor at 1.3

    return new_interval, new_ease_factor, new_repetitions
```

### SM-2 behavior table

| Scenario | quality | Result |

| First correct answer | 5 | interval=1, reps=1 |
| Second correct answer | 5 | interval=6, reps=2 |
| Third correct, EF=2.5 | 5 | interval=15, reps=3 |
| Fourth correct, EF=2.6 | 5 | interval=39, reps=4 |
| Any incorrect answer | 1 | interval=1, reps=0 (reset) |
| Correct but hesitant | 3 | interval grows, but EF decreases slightly |

### Key properties
- Ease factor (EF) never drops below 1.3
- Incorrect answer always resets to 1-day interval
- Each correct answer makes the next interval longer
- Harder questions (lower quality) get shorter intervals

### Done when
- `sm2(5, 0, 2.5, 0)` returns `(1, 2.6, 1)` -- first correct
- `sm2(5, 1, 2.6, 1)` returns `(6, 2.7, 2)` -- second correct
- `sm2(1, 3, 2.5, 15)` returns `(1, 1.7, 0)` -- incorrect resets
- Unit tests cover all scenarios in the table above

---

## Part 5 -- Attempt Recording + Schedule Update Endpoint

### Modify existing endpoint

The `POST /quiz/answer` endpoint from Week 3 needs to be extended:

```
Previous (Week 3):
  1. Grade the answer
  2. Create attempts row
  3. Return result

Updated (Week 4):
  1. Grade the answer
  2. Create attempts row
  3. Look up or create review_schedule for this user + question
  4. Map answer result to SM-2 quality score
  5. Run SM-2 algorithm
  6. Update review_schedule with new values
  7. Return result (now includes next_review_date)
```

### Files to modify

| File | Action |

| `backend/app/api/quiz.py` | Extend answer endpoint to update schedule |
| `backend/app/services/scheduler.py` | Add `update_review_schedule()` function |

### Updated AnswerResult schema

```python
class AnswerResult(BaseModel):
    is_correct: bool
    correct_answer: str
    explanation: str | None
    next_review_date: date | None   # new field
    interval_days: int | None       # new field
```

### Schedule creation logic

```
If no review_schedule exists for this user + question:
    Create one with defaults:
        ease_factor = 2.5
        interval_days = 0
        repetitions = 0
        next_review_date = today

Run SM-2 with current values + quality
Update review_schedule with new values
Set next_review_date = today + new_interval
```

### Done when
- Answering a question correctly the first time sets next_review to tomorrow
- Answering correctly again sets next_review to 6 days out
- Answering incorrectly resets next_review to tomorrow
- All schedule changes reflected in the review_schedule table
- AnswerResult includes the next review date

---

## Part 6 -- Due Reviews Endpoint + Review Mode

### Endpoints

| Method | Path | Request | Response |

| GET | `/reviews/due` | query: `limit` (default 20) | `ReviewDueList` |
| GET | `/reviews/stats` | -- | review statistics |

### Due reviews logic

```sql
SELECT rs.*, q.question_text, q.type, q.options, q.correct_answer, q.difficulty
FROM review_schedule rs
JOIN questions q ON rs.question_id = q.id
WHERE rs.user_id = :current_user_id
  AND rs.next_review_date <= CURRENT_DATE
ORDER BY rs.next_review_date ASC
LIMIT :limit
```

### Review stats response

```python
class ReviewStats(BaseModel):
    due_today: int
    due_this_week: int
    total_reviewed: int
    average_ease_factor: float
    longest_streak: int        # max consecutive correct
```

### Files to create/modify

| File | Action |

| `backend/app/api/reviews.py` | New -- due reviews + stats endpoints |
| `backend/app/api/router.py` | Add reviews router |
| `backend/app/schemas/review.py` | Add ReviewStats schema, extend ReviewDue |

### Extended ReviewDue schema

```python
class ReviewDueItem(BaseModel):
    schedule_id: uuid.UUID
    question_id: uuid.UUID
    question_text: str
    question_type: str
    options: dict | None
    difficulty: str
    ease_factor: float
    interval_days: int
    next_review_date: date
    repetitions: int
```

### Review vs new quiz
- **New quiz**: generates fresh questions from a topic via LLM
- **Review**: re-presents previously answered questions that are due for spaced review
- Both use the same QuestionCard component on the frontend
- Review answers go through the same `POST /quiz/answer` endpoint (which updates the schedule)

### Done when
- `GET /reviews/due` returns questions where `next_review_date <= today`
- `GET /reviews/stats` returns accurate counts
- After answering a due review, the question's next_review_date moves forward
- Questions not yet due do not appear in the results

---

## Part 7 -- Background Review Checker Worker

### Purpose
A scheduled job that checks for due reviews and logs/flags them. This satisfies the "triggering spaced repetition notifications" requirement from the spec without building a full push-notification system.

### Files to create

| File | Action |

| `backend/app/workers/review_checker.py` | New -- scheduled job |
| `backend/app/main.py` | Add APScheduler startup |

### Implementation

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

async def check_due_reviews():
    """Runs daily at 8:00 AM. Logs users with due reviews."""
    async with async_session() as db:
        result = await db.execute(
            select(ReviewSchedule.user_id, func.count())
            .where(ReviewSchedule.next_review_date <= date.today())
            .group_by(ReviewSchedule.user_id)
        )
        for user_id, count in result.all():
            logger.info(f"User {user_id} has {count} reviews due")
            # Future: send email or in-app notification
```

### Add to app startup

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_due_reviews, "cron", hour=8, minute=0)
    scheduler.start()
    yield
    scheduler.shutdown()
```

### Backend dependency to add

```
APScheduler>=3.10
```

### Done when
- Scheduler starts with the app (visible in startup logs)
- Daily job runs and logs users with due reviews
- Job does not crash if no reviews are due
- Job does not block the main application

---

## Part 8 -- Frontend: Due Reviews UI + Dashboard Integration

### Files to modify/create

| File | Action |

| `frontend/src/pages/DashboardPage.jsx` | Add review summary card + "Start Review" button |
| `frontend/src/pages/ReviewPage.jsx` | New -- review mode (reuses QuestionCard) |
| `frontend/src/App.jsx` | Add `/review` route |
| `frontend/src/components/Layout.jsx` | Add "Review" nav item |

### Dashboard integration

Add a review summary section to the dashboard:

```
Due for Review
--------------
12 questions due today
34 questions due this week

[Start Review]
```

Also update the existing stat cards to pull real data:

| Card | Data source |

| Documents | `GET /documents` -> count |
| Questions | `GET /quiz/topics/{id}` -> aggregate or new endpoint |
| Due Reviews | `GET /reviews/stats` -> `due_today` |
| Mastery | `GET /reviews/stats` -> `average_ease_factor` mapped to % |

### ReviewPage

```
Review Mode (12 questions due)
------------------------------
[Question 1/12]

Question text here?

[ ] A. Option one
[ ] B. Option two
[ ] C. Option three
[ ] D. Option four

                [Submit]

Progress: [=======>              ] 3/12
```

### Key difference from QuizPage
- QuizPage: user picks topic/difficulty, generates new questions
- ReviewPage: system selects questions based on SM-2 schedule, no generation

### Nav update

| Nav item | Route |

| Dashboard | `/dashboard` |
| Upload | `/upload` |
| Quiz | `/quiz` |
| Review | `/review` |
| Analytics | `/analytics` |

### Done when
- Dashboard shows real "due today" count from the API
- Clicking "Start Review" navigates to `/review`
- Review page loads due questions and lets user answer them
- After answering, next_review_date updates and the question leaves the due list
- If no reviews due, shows "No reviews due. You're all caught up."

---

## Part 9 -- Testing: Auth + SM-2 Verification

### Test files to create

| File | Purpose |

| `backend/tests/test_auth.py` | Auth endpoint tests |
| `backend/tests/test_sm2.py` | SM-2 algorithm unit tests |
| `backend/tests/test_reviews.py` | Review schedule integration tests |

### Auth tests

| Test | Expected |

| Register with valid email | 201, user created |
| Register with duplicate email | 409 |
| Login with correct credentials | 200, tokens returned |
| Login with wrong password | 401 |
| Access protected route without token | 401 |
| Access protected route with valid token | 200 |
| Access protected route with expired token | 401 |
| Refresh with valid refresh token | 200, new tokens |
| Logout then access with old token | 401 |

### SM-2 unit tests

| Test | Input (q, reps, ef, interval) | Expected (interval, ef, reps) |

| First correct | (5, 0, 2.5, 0) | (1, 2.6, 1) |
| Second correct | (5, 1, 2.6, 1) | (6, 2.7, 2) |
| Third correct | (5, 2, 2.7, 6) | (16, 2.8, 3) |
| Incorrect resets | (1, 3, 2.5, 15) | (1, 1.7, 0) |
| Hesitant correct | (3, 0, 2.5, 0) | (1, 2.36, 1) |
| EF floor at 1.3 | (1, 0, 1.3, 0) | (1, 1.3, 0) |
| After reset, correct again | (5, 0, 1.7, 1) | (1, 1.8, 1) |

### Review schedule integration tests

| Test | Steps |

| Schedule creation | Answer a question -> verify review_schedule row created |
| Interval growth | Answer correctly 3 times -> verify interval grows each time |
| Reset on failure | Answer correctly twice, then incorrectly -> verify interval resets to 1 |
| Due query accuracy | Set next_review_date to yesterday -> verify it appears in `/reviews/due` |
| Future not due | Set next_review_date to tomorrow -> verify it does NOT appear in `/reviews/due` |

### Done when
- All auth tests pass
- All SM-2 unit tests pass (7 scenarios)
- Review schedule integration tests verify the full cycle
- Manual verification: answer the same question 4 times in sequence, observe interval changes in the DB

---

## Dependency Graph

```
Part 1 (Auth API)
  |
Part 2 (Middleware)       Part 4 (SM-2 algorithm)
  |                           |
Part 3 (Frontend auth)   Part 5 (Attempt + schedule update)
  |                           |
  +---------+---------+   Part 6 (Due reviews endpoint)
            |                 |
            |             Part 7 (Background worker)
            |                 |
            +-------+---------+
                    |
              Part 8 (Frontend: reviews UI + dashboard)
                    |
              Part 9 (Testing)
```

Parts 1-3 (auth) and Parts 4-7 (SM-2/reviews) are two independent tracks that can be developed in parallel. They merge at Part 8 (frontend) since the review UI needs both auth and scheduling.

---

## Risk Notes

- **JWT token management is the biggest UX risk.** If the refresh flow is buggy, users get randomly logged out. Test the interceptor thoroughly, especially the race condition where multiple requests fail simultaneously and all try to refresh at once. Use a mutex/flag to ensure only one refresh happens.
- **SM-2 is simple to implement but easy to get wrong.** The ease factor formula has specific constants (0.1, 0.08, 0.02) that must be exact. Copy them directly from the original SuperMemo 2 paper, don't try to simplify.
- **Don't overbuild the background worker.** A log-only daily check is sufficient for the spec. Email/push notifications are scope creep for v1.
- **APScheduler + async.** Use `AsyncIOScheduler`, not the default `BackgroundScheduler`. The default will block the event loop.

---

## Files Created/Modified Summary

| File | Action | Part |

| `backend/app/api/auth.py` | New | 1 |
| `backend/app/api/router.py` | Modified | 1, 6 |
| `backend/app/core/deps.py` | New | 2 |
| `backend/app/api/documents.py` | Modified (add auth) | 2 |
| `backend/app/api/quiz.py` | Modified (add auth + schedule) | 2, 5 |
| `frontend/src/hooks/useAuth.jsx` | New | 3 |
| `frontend/src/components/ProtectedRoute.jsx` | New | 3 |
| `frontend/src/pages/LoginPage.jsx` | Modified | 3 |
| `frontend/src/pages/RegisterPage.jsx` | Modified | 3 |
| `frontend/src/App.jsx` | Modified | 3, 8 |
| `frontend/src/api/client.js` | Modified | 3 |
| `backend/app/services/scheduler.py` | New | 4 |
| `backend/app/api/reviews.py` | New | 6 |
| `backend/app/schemas/review.py` | Modified | 6 |
| `backend/app/schemas/question.py` | Modified | 5 |
| `backend/app/workers/review_checker.py` | New | 7 |
| `backend/app/main.py` | Modified | 7 |
| `backend/requirements.txt` | Modified (add APScheduler) | 7 |
| `frontend/src/pages/DashboardPage.jsx` | Modified | 8 |
| `frontend/src/pages/ReviewPage.jsx` | New | 8 |
| `frontend/src/components/Layout.jsx` | Modified | 8 |
| `backend/tests/test_auth.py` | New | 9 |
| `backend/tests/test_sm2.py` | New | 9 |
| `backend/tests/test_reviews.py` | New | 9 |
