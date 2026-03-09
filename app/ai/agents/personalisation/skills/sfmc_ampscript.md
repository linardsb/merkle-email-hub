# SFMC AMPscript Syntax Reference

## Variable Declaration

### SET
```ampscript
%%[
SET @firstName = AttributeValue("FirstName")
SET @lastName = AttributeValue("LastName")
SET @email = AttributeValue("EmailAddress")
SET @city = AttributeValue("City")
]%%
```

### With Default/Fallback
```ampscript
%%[
SET @firstName = AttributeValue("FirstName")
IF Empty(@firstName) THEN
  SET @firstName = "there"
ENDIF
]%%
```

## Output

### Inline Output
```ampscript
%%=v(@firstName)=%%
%%=ProperCase(@firstName)=%%
```

### In HTML
```html
<td>Hi %%=v(@firstName)=%%, welcome back!</td>
```

## String Functions

```ampscript
%%=ProperCase(@firstName)=%%
%%=Uppercase(@city)=%%
%%=Lowercase(@email)=%%
%%=Trim(@value)=%%
%%=Substring(@text, 1, 20)=%%
%%=Length(@text)=%%
%%=Replace(@text, "old", "new")=%%
%%=Concat(@firstName, " ", @lastName)=%%
```

## Date Functions

```ampscript
%%=Now()=%%
%%=Format(Now(), "MMMM dd, yyyy")=%%
%%=DateAdd(Now(), 7, "D")=%%
%%=DateDiff(Now(), @expiryDate, "D")=%%
%%=FormatDate(@date, "MM/dd/yyyy")=%%
```

## Lookup Functions

### Lookup (Single Value)
```ampscript
%%[
SET @productName = Lookup("ProductCatalog", "ProductName", "ProductID", @productId)
]%%
```

### LookupRows (Multiple Rows)
```ampscript
%%[
SET @rows = LookupRows("OrderHistory", "CustomerID", @customerId)
SET @rowCount = RowCount(@rows)
FOR @i = 1 TO @rowCount DO
  SET @row = Row(@rows, @i)
  SET @orderDate = Field(@row, "OrderDate")
  SET @orderTotal = Field(@row, "Total")
]%%
<tr>
  <td>%%=FormatDate(@orderDate, "MM/dd/yyyy")=%%</td>
  <td>%%=Format(@orderTotal, "$#,##0.00")=%%</td>
</tr>
%%[NEXT @i]%%
```

## Conditionals

### IF/ELSE
```ampscript
%%[
IF @membershipTier == "Gold" THEN
]%%
  <td>Exclusive Gold Member Offer</td>
%%[
ELSEIF @membershipTier == "Silver" THEN
]%%
  <td>Silver Member Special</td>
%%[
ELSE
]%%
  <td>Join Our Loyalty Program</td>
%%[
ENDIF
]%%
```

### Nested IF
```ampscript
%%[
IF NOT Empty(@firstName) THEN
  IF @gender == "F" THEN
    SET @greeting = Concat("Dear Ms. ", @lastName)
  ELSE
    SET @greeting = Concat("Dear Mr. ", @lastName)
  ENDIF
ELSE
  SET @greeting = "Dear Valued Customer"
ENDIF
]%%
```

## Data Extensions

### Create DE Row
```ampscript
%%[InsertDE("LogTable", "Email", @email, "Action", "Opened", "Date", Now())]%%
```

### Update DE Row
```ampscript
%%[UpsertDE("Preferences", 1, "Email", @email, "LastEmail", Now())]%%
```

## Common Patterns

### Personalized Greeting
```ampscript
%%[
SET @firstName = AttributeValue("FirstName")
IF Empty(@firstName) THEN
  SET @firstName = "there"
ENDIF
]%%
<td>Hi %%=ProperCase(@firstName)=%%, </td>
```

### Dynamic Content by Segment
```ampscript
%%[
SET @segment = AttributeValue("CustomerSegment")
]%%
%%[IF @segment == "VIP" THEN]%%
  {{VIP content here}}
%%[ELSEIF @segment == "Returning" THEN]%%
  {{Returning customer content}}
%%[ELSE]%%
  {{New customer content}}
%%[ENDIF]%%
```

## Error Handling

```ampscript
%%[
SET @value = AttributeValue("FieldName")
IF Empty(@value) OR @value == "" THEN
  SET @value = "Default Value"
ENDIF
]%%
```

Always check for empty values before using them in output or functions.
