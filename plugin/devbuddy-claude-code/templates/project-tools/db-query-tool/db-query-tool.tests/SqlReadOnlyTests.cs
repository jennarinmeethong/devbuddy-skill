using Xunit;

namespace BmsReadonlyDatabaseQuery.Tests;

public sealed class SqlReadOnlyTests
{
    [Fact]
    public void AllowsSelectAndCte()
    {
        var queries = new[]
        {
            "SELECT 1",
            "SELECT TOP (10) Id FROM dbo.ApprovedView WHERE Code = 'BMS'",
            "WITH items AS (SELECT Id FROM dbo.ApprovedView) SELECT Id FROM items",
        };

        foreach (var query in queries)
        {
            var result = SqlReadOnly.Parameterize(query, null);
            Assert.NotNull(result.Sql);
        }
    }

    [Fact]
    public void RejectsWritesAndUnsafeSources()
    {
        var queries = new[]
        {
            "INSERT INTO dbo.Items (Name) VALUES ('x')",
            "UPDATE dbo.Items SET Name = 'x'",
            "DELETE FROM dbo.Items",
            "MERGE dbo.Items AS target USING dbo.Other AS source ON 1=0 WHEN NOT MATCHED THEN INSERT DEFAULT VALUES",
            "EXEC dbo.GetItems",
            "SELECT Id INTO #items FROM dbo.ApprovedView",
            "SELECT Id FROM dbo.ApprovedView; SELECT Id FROM dbo.ApprovedView",
            "SELECT Id FROM otherdb.dbo.ApprovedView",
            "SELECT * FROM OPENROWSET(BULK 'items.csv', SINGLE_CLOB) AS source",
            "SELECT Id FROM dbo.ApprovedView WITH (NOLOCK)",
            "SELECT Id FROM dbo.ApprovedView OPTION (MAXRECURSION 0)",
            "SELECT Id FROM dbo.GetRows()",
        };

        foreach (var query in queries)
        {
            Assert.Throws<SqlValidationException>(() => SqlReadOnly.Parameterize(query, null));
        }
    }

    [Fact]
    public void ParameterizationUsesBoundParametersAndRejectsUnusedValues()
    {
        using var document = System.Text.Json.JsonDocument.Parse("{\"code\":\"BMS\"}");
        var result = SqlReadOnly.Parameterize(
            "SELECT Id FROM dbo.ApprovedView WHERE Code = @code",
            document.RootElement.Clone());

        Assert.Contains("@p0", result.Sql);
        Assert.Single(result.Bindings);
        Assert.Equal("BMS", result.Bindings[0].Value);

        using var duplicateDocument = System.Text.Json.JsonDocument.Parse("{\"@p\":1,\"p\":2}");
        Assert.Throws<SqlValidationException>(() => SqlReadOnly.Parameterize("SELECT @p", duplicateDocument.RootElement.Clone()));
    }

    [Fact]
    public void RejectsInvalidParameterShapesAndLimits()
    {
        using var array = System.Text.Json.JsonDocument.Parse("[]");
        Assert.Throws<SqlValidationException>(() => SqlReadOnly.Parameterize("SELECT 1", array.RootElement.Clone()));

        using var longValue = System.Text.Json.JsonDocument.Parse("{\"p\":\"" + new string('x', 4001) + "\"}");
        Assert.Throws<SqlValidationException>(() => SqlReadOnly.Parameterize("SELECT @p", longValue.RootElement.Clone()));
    }
}
