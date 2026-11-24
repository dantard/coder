"""
Operational Transformation for plain text.

An operation is a list of components that walks over the whole document:
    int > 0  -> retain n characters
    int < 0  -> delete n characters
    str      -> insert the string

This is the same model used by ot.js / Google Wave. Shared by server and client.
"""


def _is_retain(c):
    return isinstance(c, int) and c > 0


def _is_delete(c):
    return isinstance(c, int) and c < 0


def _is_insert(c):
    return isinstance(c, str)


class TextOperation:
    def __init__(self, ops=None):
        self.ops = []
        self.base_length = 0    # length of the document the op applies to
        self.target_length = 0  # length of the document after applying it
        for c in ops or []:
            if _is_retain(c):
                self.retain(c)
            elif _is_delete(c):
                self.delete(-c)
            elif _is_insert(c):
                self.insert(c)
            else:
                raise ValueError(f"invalid op component: {c!r}")

    # ---- builders -------------------------------------------------------
    def retain(self, n):
        if n <= 0:
            return self
        self.base_length += n
        self.target_length += n
        if self.ops and _is_retain(self.ops[-1]):
            self.ops[-1] += n
        else:
            self.ops.append(n)
        return self

    def insert(self, s):
        if not s:
            return self
        self.target_length += len(s)
        ops = self.ops
        if ops and _is_insert(ops[-1]):
            ops[-1] += s
        elif ops and _is_delete(ops[-1]):
            # keep canonical order: insert before delete
            if len(ops) > 1 and _is_insert(ops[-2]):
                ops[-2] += s
            else:
                ops.insert(len(ops) - 1, s)
        else:
            ops.append(s)
        return self

    def delete(self, n):
        if n <= 0:
            return self
        self.base_length += n
        if self.ops and _is_delete(self.ops[-1]):
            self.ops[-1] -= n
        else:
            self.ops.append(-n)
        return self

    # ---- helpers --------------------------------------------------------
    def is_noop(self):
        return len(self.ops) == 0 or (len(self.ops) == 1 and _is_retain(self.ops[0]))

    def to_json(self):
        return list(self.ops)

    @classmethod
    def from_json(cls, data):
        return cls(data)

    @classmethod
    def from_diff(cls, old, new):
        """Build the op that turns `old` into `new` (single changed region)."""
        start = 0
        max_start = min(len(old), len(new))
        while start < max_start and old[start] == new[start]:
            start += 1
        end_old, end_new = len(old), len(new)
        while end_old > start and end_new > start and old[end_old - 1] == new[end_new - 1]:
            end_old -= 1
            end_new -= 1
        op = cls()
        op.retain(start)
        op.delete(end_old - start)
        op.insert(new[start:end_new])
        op.retain(len(old) - end_old)
        return op

    def __repr__(self):
        return f"TextOperation({self.ops!r})"

    def __eq__(self, other):
        return isinstance(other, TextOperation) and self.ops == other.ops

    # ---- core -----------------------------------------------------------
    def apply(self, doc):
        if len(doc) != self.base_length:
            raise ValueError(
                f"op base length {self.base_length} != document length {len(doc)}")
        out, i = [], 0
        for c in self.ops:
            if _is_retain(c):
                out.append(doc[i:i + c])
                i += c
            elif _is_insert(c):
                out.append(c)
            else:
                i -= c
        return "".join(out)

    def compose(self, other):
        """Return an op equivalent to applying self, then other."""
        if self.target_length != other.base_length:
            raise ValueError("compose: lengths do not match")
        res = TextOperation()
        ops1, ops2 = list(self.ops), list(other.ops)
        i1 = i2 = 0
        op1 = ops1[0] if ops1 else None
        op2 = ops2[0] if ops2 else None

        def n1():
            nonlocal i1
            i1 += 1
            return ops1[i1] if i1 < len(ops1) else None

        def n2():
            nonlocal i2
            i2 += 1
            return ops2[i2] if i2 < len(ops2) else None

        while op1 is not None or op2 is not None:
            if op1 is not None and _is_delete(op1):
                res.delete(-op1)
                op1 = n1()
                continue
            if op2 is not None and _is_insert(op2):
                res.insert(op2)
                op2 = n2()
                continue
            if op1 is None or op2 is None:
                raise ValueError("compose: operation too short")

            if _is_retain(op1) and _is_retain(op2):
                if op1 > op2:
                    res.retain(op2); op1 -= op2; op2 = n2()
                elif op1 == op2:
                    res.retain(op1); op1 = n1(); op2 = n2()
                else:
                    res.retain(op1); op2 -= op1; op1 = n1()
            elif _is_insert(op1) and _is_delete(op2):
                if len(op1) > -op2:
                    op1 = op1[-op2:]; op2 = n2()
                elif len(op1) == -op2:
                    op1 = n1(); op2 = n2()
                else:
                    op2 += len(op1); op1 = n1()
            elif _is_insert(op1) and _is_retain(op2):
                if len(op1) > op2:
                    res.insert(op1[:op2]); op1 = op1[op2:]; op2 = n2()
                elif len(op1) == op2:
                    res.insert(op1); op1 = n1(); op2 = n2()
                else:
                    res.insert(op1); op2 -= len(op1); op1 = n1()
            elif _is_retain(op1) and _is_delete(op2):
                if op1 > -op2:
                    res.delete(-op2); op1 += op2; op2 = n2()
                elif op1 == -op2:
                    res.delete(-op2); op1 = n1(); op2 = n2()
                else:
                    res.delete(op1); op2 += op1; op1 = n1()
            else:
                raise ValueError("compose: unreachable")
        return res

    @staticmethod
    def transform(a, b):
        """
        Given concurrent ops a and b (same base document) return (a', b') such
        that apply(apply(doc, a), b') == apply(apply(doc, b), a').
        On a tie (both insert at the same spot) a's insert goes first.
        """
        if a.base_length != b.base_length:
            raise ValueError("transform: base lengths differ")
        a2, b2 = TextOperation(), TextOperation()
        ops1, ops2 = list(a.ops), list(b.ops)
        i1 = i2 = 0
        op1 = ops1[0] if ops1 else None
        op2 = ops2[0] if ops2 else None

        def n1():
            nonlocal i1
            i1 += 1
            return ops1[i1] if i1 < len(ops1) else None

        def n2():
            nonlocal i2
            i2 += 1
            return ops2[i2] if i2 < len(ops2) else None

        while op1 is not None or op2 is not None:
            if op1 is not None and _is_insert(op1):
                a2.insert(op1); b2.retain(len(op1)); op1 = n1()
                continue
            if op2 is not None and _is_insert(op2):
                a2.retain(len(op2)); b2.insert(op2); op2 = n2()
                continue
            if op1 is None or op2 is None:
                raise ValueError("transform: operation too short")

            if _is_retain(op1) and _is_retain(op2):
                m = min(op1, op2)
                a2.retain(m); b2.retain(m)
                if op1 > op2:
                    op1 -= op2; op2 = n2()
                elif op1 == op2:
                    op1 = n1(); op2 = n2()
                else:
                    op2 -= op1; op1 = n1()
            elif _is_delete(op1) and _is_delete(op2):
                # both delete the same text: nothing to do for that part
                if -op1 > -op2:
                    op1 -= op2; op2 = n2()
                elif op1 == op2:
                    op1 = n1(); op2 = n2()
                else:
                    op2 -= op1; op1 = n1()
            elif _is_delete(op1) and _is_retain(op2):
                m = min(-op1, op2)
                a2.delete(m)
                if -op1 > op2:
                    op1 += op2; op2 = n2()
                elif -op1 == op2:
                    op1 = n1(); op2 = n2()
                else:
                    op2 += op1; op1 = n1()
            elif _is_retain(op1) and _is_delete(op2):
                m = min(op1, -op2)
                b2.delete(m)
                if op1 > -op2:
                    op1 += op2; op2 = n2()
                elif op1 == -op2:
                    op1 = n1(); op2 = n2()
                else:
                    op2 += op1; op1 = n1()
            else:
                raise ValueError("transform: unreachable")
        return a2, b2


def transform_index(op, index):
    """Move a cursor position through an operation."""
    new_index, pos = index, 0
    for c in op.ops:
        if pos > index:
            break
        if _is_retain(c):
            pos += c
        elif _is_insert(c):
            new_index += len(c)
        else:
            new_index -= min(index - pos, -c)
            pos -= c
    return max(0, new_index)
