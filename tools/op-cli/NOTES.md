# OpenProject API gotchas

Each of these cost real debugging time. Recorded so they cost it once.

## Formattable custom fields need `{format, raw}`, not a string

`Paths` is a *text* custom field. Writing `{"customField2": "apps/api/x.py"}`
returns **200 OK and silently stores an empty value**. It must be
`{"customField2": {"format": "markdown", "raw": "apps/api/x.py"}}`.

Silent success on a malformed write is the worst failure mode here — nothing
in the response says the value was dropped. `main.py::text_field()` is the one
place that builds these.

## The form endpoint needs `lockVersion` in its body

`POST /api/v3/work_packages/{id}/form` with `{}` answers **409 Conflict**,
which reads like a concurrent-edit problem and is really just a malformed
request. Pass `{"lockVersion": n}`.

## Workflows differ per type, and Task's default is minimal

Out of the box, **Task** only permits New, In progress, Closed, On hold,
Rejected — no `In testing`, no `Test failed`. **Bug** has the full lifecycle.
So `In progress -> In testing` on a Task fails with a 422 that does not
mention workflows at all.

Fixed by copying Bug's workflow rows onto Task, Feature and Epic:

```ruby
src = Workflow.where(type_id: Type.find_by(name: "Bug").id)
# ... create the same (role, old_status, new_status) rows for the other types
```

`client.py::allowed_transitions()` now asks first, so an illegal move reports
what *is* legal instead of a bare 422.

## Custom fields cannot be created through API v3

It is an admin operation. Use `rails runner`. Only one-time setup needs this;
op-cli itself is pure REST.

## Git Bash rewrites container paths

`docker compose exec web rails runner /tmp/x.rb` becomes
`C:/Users/.../Temp/x.rb` before it reaches the container. Use
`MSYS_NO_PATHCONV=1` and a leading `//tmp/x.rb`.
